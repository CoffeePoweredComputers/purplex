/**
 * Python Type System Utilities
 * Provides comprehensive type detection, validation, and conversion for Python types
 */

// ===== TYPE DEFINITIONS =====

export interface TypeSpec {
  type: string;
  elementType?: TypeSpec;
  keyType?: TypeSpec;
  valueType?: TypeSpec;
  innerType?: TypeSpec;
  unionTypes?: TypeSpec[];
  literalValues?: unknown[];
}

export interface ValidationResult {
  valid: boolean;
  error?: string;
  path: string[];
  suggestion?: string;
}

export interface TypeDetectionResult {
  detected: string;
  annotation: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface TypeHandler {
  validate: RegExp;
  convert: (value: string) => unknown;
  placeholder: string;
  examples?: string[];
  description?: string;
}

export interface TypeConversionError extends Error {
  originalValue: string;
  expectedType: string;
  suggestion?: string;
}


// ===== ENHANCED TYPE HANDLERS =====

export const pythonTypes: Record<string, TypeHandler> = {
  // Basic types
  'int': { 
    validate: /^-?\d+$/, 
    convert: (v: string): number => {
      const result = parseInt(v, 10);
      if (isNaN(result)) {
        throw new Error(`Cannot convert "${v}" to integer`);
      }
      return result;
    },
    placeholder: '42',
    examples: ['0', '42', '-17'],
    description: 'Integer number'
  },
  
  'float': { 
    validate: /^-?\d*\.?\d+([eE][+-]?\d+)?$/, 
    convert: (v: string): number => {
      const result = parseFloat(v);
      if (isNaN(result)) {
        throw new Error(`Cannot convert "${v}" to float`);
      }
      return result;
    },
    placeholder: '3.14',
    examples: ['3.14', '-2.5', '1e-10'],
    description: 'Floating point number'
  },
  
  'str': { 
    validate: /.*/, 
    convert: (v: string): string => {
      // Remove quotes if present
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
        return v.slice(1, -1);
      }
      return String(v);
    },
    placeholder: 'hello world',
    examples: ['hello', '"quoted string"', 'text with spaces'],
    description: 'Text string'
  },
  
  'bool': { 
    validate: /^(true|false|True|False|yes|no|1|0)$/i, 
    convert: (v: string): boolean => {
      const lower = v.toLowerCase();
      return lower === 'true' || lower === 'yes' || lower === '1';
    },
    placeholder: 'true',
    examples: ['true', 'false', 'True', 'False'],
    description: 'Boolean value'
  },
  
  // Collections
  'list': { 
    validate: /^\[.*\]$/, 
    convert: (v: string): unknown[] => {
      try {
        const result = JSON.parse(v);
        if (!Array.isArray(result)) {
          throw new Error('Not an array');
        }
        return result;
      } catch {
        throw new Error(`Cannot parse "${v}" as list`);
      }
    },
    placeholder: '[1, 2, 3]',
    examples: ['[]', '[1, 2, 3]', '["a", "b"]'],
    description: 'List of values'
  },
  
  'dict': { 
    validate: /^\{.*\}$/, 
    convert: (v: string): Record<string, unknown> => {
      try {
        const result = JSON.parse(v);
        if (typeof result !== 'object' || result === null || Array.isArray(result)) {
          throw new Error('Not an object');
        }
        return result;
      } catch {
        throw new Error(`Cannot parse "${v}" as dict`);
      }
    },
    placeholder: '{"key": "value"}',
    examples: ['{}', '{"a": 1}', '{"name": "John", "age": 30}'],
    description: 'Dictionary/object with key-value pairs'
  },
  
  'tuple': { 
    validate: /^\(.*\)$/, 
    convert: (v: string): unknown[] => {
      try {
        // Convert tuple notation to array
        const arrayStr = v.replace(/^\(/, '[').replace(/\)$/, ']');
        const result = JSON.parse(arrayStr);
        if (!Array.isArray(result)) {
          throw new Error('Not a tuple');
        }
        return result;
      } catch {
        throw new Error(`Cannot parse "${v}" as tuple`);
      }
    },
    placeholder: '(1, 2, 3)',
    examples: ['()', '(1, 2)', '("a", "b", "c")'],
    description: 'Tuple (immutable list)'
  },
  
  'set': { 
    validate: /^\{.*\}$/, 
    convert: (v: string): unknown[] => {
      try {
        // Try parsing as array first (JSON set notation)
        if (v.startsWith('[') && v.endsWith(']')) {
          return JSON.parse(v);
        }
        
        // Parse as object and extract unique values
        const parsed = JSON.parse(v);
        if (Array.isArray(parsed)) {
          return [...new Set(parsed)];
        } else if (typeof parsed === 'object' && parsed !== null) {
          return [...new Set(Object.values(parsed))];
        }
        throw new Error('Invalid set format');
      } catch {
        throw new Error(`Cannot parse "${v}" as set`);
      }
    },
    placeholder: '{1, 2, 3}',
    examples: ['{1, 2, 3}', '{"a", "b"}', 'set()'],
    description: 'Set of unique values'
  },
  
  // Special types
  'None': { 
    validate: /^(None|null|none|NULL)$/i, 
    convert: (): null => null,
    placeholder: 'None',
    examples: ['None', 'null'],
    description: 'None/null value'
  },
  
  'Any': { 
    validate: /.*/, 
    convert: (v: string): unknown => autoDetectAndConvert(v),
    placeholder: 'any value',
    examples: ['42', '"text"', '[1, 2, 3]'],
    description: 'Any type of value'
  }
};

// ===== ENHANCED TYPE ANNOTATION PARSING =====

export function parseTypeAnnotation(typeStr: string): TypeSpec {
  return parseTypeAnnotationInternal(typeStr.trim());
}

function parseTypeAnnotationInternal(typeStr: string): TypeSpec {
  // Handle Union[T1, T2, ...] types
  if (typeStr.startsWith('Union[') && typeStr.endsWith(']')) {
    const inner = typeStr.slice(6, -1);
    const unionTypes = parseUnionTypes(inner);
    return { type: 'Union', unionTypes };
  }

  // Handle Optional[T] by converting to Union[T, None]
  if (typeStr.startsWith('Optional[') && typeStr.endsWith(']')) {
    const inner = typeStr.slice(9, -1);
    return { 
      type: 'Union', 
      unionTypes: [parseTypeAnnotation(inner), { type: 'None' }] 
    };
  }

  // Handle Literal[val1, val2, ...] types
  if (typeStr.startsWith('Literal[') && typeStr.endsWith(']')) {
    const inner = typeStr.slice(8, -1);
    const literalValues = parseLiteralValues(inner);
    return { type: 'Literal', literalValues };
  }
  
  // Handle List[T] and list[T]
  if ((typeStr.startsWith('List[') || typeStr.startsWith('list[')) && typeStr.endsWith(']')) {
    const start = typeStr.indexOf('[') + 1;
    const inner = typeStr.slice(start, -1);
    return { type: 'list', elementType: parseTypeAnnotation(inner) };
  }
  
  // Handle Dict[K, V] and dict[K, V]
  if ((typeStr.startsWith('Dict[') || typeStr.startsWith('dict[')) && typeStr.endsWith(']')) {
    const start = typeStr.indexOf('[') + 1;
    const inner = typeStr.slice(start, -1);
    
    const commaIndex = findTopLevelComma(inner);
    if (commaIndex !== -1) {
      const keyType = inner.slice(0, commaIndex).trim();
      const valueType = inner.slice(commaIndex + 1).trim();
      return {
        type: 'dict',
        keyType: parseTypeAnnotation(keyType),
        valueType: parseTypeAnnotation(valueType)
      };
    }
  }
  
  // Handle Set[T] and set[T]
  if ((typeStr.startsWith('Set[') || typeStr.startsWith('set[')) && typeStr.endsWith(']')) {
    const start = typeStr.indexOf('[') + 1;
    const inner = typeStr.slice(start, -1);
    return { type: 'set', elementType: parseTypeAnnotation(inner) };
  }
  
  // Handle Tuple[T, ...] and tuple[T, ...]
  if ((typeStr.startsWith('Tuple[') || typeStr.startsWith('tuple[')) && typeStr.endsWith(']')) {
    const start = typeStr.indexOf('[') + 1;
    const inner = typeStr.slice(start, -1);
    return { type: 'tuple', elementType: parseTypeAnnotation(inner.replace(/,\s*\.\.\./, '')) };
  }
  
  // Handle basic types
  const basicTypes = ['int', 'float', 'str', 'bool', 'None', 'Any'];
  if (basicTypes.includes(typeStr)) {
    return { type: typeStr };
  }
  
  // Default to Any for unknown types
  return { type: 'Any' };
}

// ===== HELPER FUNCTIONS =====

function parseUnionTypes(unionStr: string): TypeSpec[] {
  const types: TypeSpec[] = [];
  let current = '';
  let depth = 0;
  
  for (let i = 0; i < unionStr.length; i++) {
    const char = unionStr[i];
    
    if (char === '[') {
      depth++;
    } else if (char === ']') {
      depth--;
    } else if (char === ',' && depth === 0) {
      if (current.trim()) {
        types.push(parseTypeAnnotation(current.trim()));
      }
      current = '';
      continue;
    }
    
    current += char;
  }
  
  if (current.trim()) {
    types.push(parseTypeAnnotation(current.trim()));
  }
  
  return types;
}

function parseLiteralValues(literalStr: string): unknown[] {
  const values: unknown[] = [];
  let current = '';
  let depth = 0;
  let inString = false;
  let stringChar = '';
  
  for (let i = 0; i < literalStr.length; i++) {
    const char = literalStr[i];
    
    if (!inString && (char === '"' || char === "'")) {
      inString = true;
      stringChar = char;
    } else if (inString && char === stringChar && literalStr[i - 1] !== '\\') {
      inString = false;
      stringChar = '';
    } else if (!inString) {
      if (char === '[' || char === '(') {
        depth++;
      } else if (char === ']' || char === ')') {
        depth--;
      } else if (char === ',' && depth === 0) {
        if (current.trim()) {
          values.push(parseLiteralValue(current.trim()));
        }
        current = '';
        continue;
      }
    }
    
    current += char;
  }
  
  if (current.trim()) {
    values.push(parseLiteralValue(current.trim()));
  }
  
  return values;
}

function parseLiteralValue(value: string): unknown {
  // Try to parse as JSON first
  try {
    return JSON.parse(value);
  } catch {
    // Return as string if JSON parsing fails
    return value.replace(/^["']|["']$/g, '');
  }
}

function findTopLevelComma(str: string): number {
  let depth = 0;
  let inString = false;
  let stringChar = '';
  
  for (let i = 0; i < str.length; i++) {
    const char = str[i];
    
    if (!inString && (char === '"' || char === "'")) {
      inString = true;
      stringChar = char;
    } else if (inString && char === stringChar && str[i - 1] !== '\\') {
      inString = false;
      stringChar = '';
    } else if (!inString) {
      if (char === '[' || char === '(') {
        depth++;
      } else if (char === ']' || char === ')') {
        depth--;
      } else if (char === ',' && depth === 0) {
        return i;
      }
    }
  }
  
  return -1;
}

// ===== ENHANCED VALIDATION =====

export function validateValueAgainstType(
  value: unknown, 
  typeSpec: TypeSpec, 
  path: string[] = []
): ValidationResult {
  // Handle Any type - always valid
  if (typeSpec.type === 'Any') {
    return { valid: true, path };
  }
  
  // Handle Union types
  if (typeSpec.type === 'Union' && typeSpec.unionTypes) {
    for (const unionType of typeSpec.unionTypes) {
      const result = validateValueAgainstType(value, unionType, path);
      if (result.valid) {
        return result;
      }
    }
    
    const typeOptions = typeSpec.unionTypes.map(t => formatTypeSpec(t)).join(' | ');
    return { 
      valid: false, 
      error: `Value doesn't match any of: ${typeOptions}`,
      path,
      suggestion: generateUnionTypeSuggestion(value, typeSpec.unionTypes)
    };
  }

  // Handle Literal types
  if (typeSpec.type === 'Literal' && typeSpec.literalValues) {
    const isValid = typeSpec.literalValues.some(literal => 
      JSON.stringify(literal) === JSON.stringify(value)
    );
    
    if (!isValid) {
      const validValues = typeSpec.literalValues.map(v => JSON.stringify(v)).join(', ');
      return {
        valid: false,
        error: `Value must be one of: ${validValues}`,
        path,
        suggestion: `Try: ${typeSpec.literalValues[0]}`
      };
    }
    
    return { valid: true, path };
  }
  
  // Handle None type
  if (typeSpec.type === 'None') {
    if (value === null || value === undefined) {
      return { valid: true, path };
    }
    return { 
      valid: false, 
      error: `Expected None but got ${getValueTypeDescription(value)}`,
      path,
      suggestion: 'Use None or null'
    };
  }
  
  // Handle primitive types with enhanced error messages
  if (['int', 'float', 'str', 'bool'].includes(typeSpec.type)) {
    return validatePrimitiveType(value, typeSpec.type, path);
  }
  
  // Handle collection types
  if (typeSpec.type === 'list') {
    return validateListType(value, typeSpec, path);
  }
  
  if (typeSpec.type === 'dict') {
    return validateDictType(value, typeSpec, path);
  }
  
  if (typeSpec.type === 'set') {
    return validateSetType(value, typeSpec, path);
  }
  
  if (typeSpec.type === 'tuple') {
    return validateTupleType(value, typeSpec, path);
  }
  
  // Unknown type - assume valid
  return { valid: true, path };
}

function validatePrimitiveType(value: unknown, expectedType: string, path: string[]): ValidationResult {
  switch (expectedType) {
    case 'int':
      if (typeof value === 'number' && Number.isInteger(value)) {
        return { valid: true, path };
      }
      return { 
        valid: false, 
        error: `Expected int but got ${getValueTypeDescription(value)}`,
        path,
        suggestion: generateIntSuggestion(value)
      };
      
    case 'float':
      if (typeof value === 'number') {
        return { valid: true, path };
      }
      return { 
        valid: false, 
        error: `Expected float but got ${getValueTypeDescription(value)}`,
        path,
        suggestion: generateFloatSuggestion(value)
      };
      
    case 'str':
      if (typeof value === 'string') {
        return { valid: true, path };
      }
      return { 
        valid: false, 
        error: `Expected str but got ${getValueTypeDescription(value)}`,
        path,
        suggestion: generateStrSuggestion(value)
      };
      
    case 'bool':
      if (typeof value === 'boolean') {
        return { valid: true, path };
      }
      return { 
        valid: false, 
        error: `Expected bool but got ${getValueTypeDescription(value)}`,
        path,
        suggestion: generateBoolSuggestion(value)
      };
      
    default:
      return { valid: true, path };
  }
}

function validateListType(value: unknown, typeSpec: TypeSpec, path: string[]): ValidationResult {
  if (!Array.isArray(value)) {
    return { 
      valid: false, 
      error: `Expected list but got ${getValueTypeDescription(value)}`,
      path,
      suggestion: 'Use array notation: [item1, item2, ...]'
    };
  }
  
  // Validate each element
  for (let i = 0; i < value.length; i++) {
    const result = validateValueAgainstType(
      value[i], 
      typeSpec.elementType || { type: 'Any' },
      [...path, `[${i}]`]
    );
    if (!result.valid) {
      return result;
    }
  }
  
  return { valid: true, path };
}

function validateDictType(value: unknown, typeSpec: TypeSpec, path: string[]): ValidationResult {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return { 
      valid: false, 
      error: `Expected dict but got ${getValueTypeDescription(value)}`,
      path,
      suggestion: 'Use object notation: {"key": "value"}'
    };
  }
  
  // Validate each key-value pair
  for (const [key, val] of Object.entries(value)) {
    // Validate key type if specified
    if (typeSpec.keyType && typeSpec.keyType.type !== 'Any') {
      const keyResult = validateValueAgainstType(key, typeSpec.keyType, [...path, `.${key}`]);
      if (!keyResult.valid) {
        return {
          ...keyResult,
          error: `Invalid key type: ${keyResult.error}`
        };
      }
    }
    
    // Validate value type
    const valueResult = validateValueAgainstType(
      val,
      typeSpec.valueType || { type: 'Any' },
      [...path, `["${key}"]`]
    );
    if (!valueResult.valid) {
      return valueResult;
    }
  }
  
  return { valid: true, path };
}

function validateSetType(value: unknown, typeSpec: TypeSpec, path: string[]): ValidationResult {
  if (!Array.isArray(value)) {
    return { 
      valid: false, 
      error: `Expected set but got ${getValueTypeDescription(value)}`,
      path,
      suggestion: 'Use array notation for set: [item1, item2, ...]'
    };
  }
  
  // Check for duplicates
  const unique = [...new Set(value.map(v => JSON.stringify(v)))];
  if (unique.length !== value.length) {
    return {
      valid: false,
      error: 'Set contains duplicate values',
      path,
      suggestion: 'Remove duplicate values from the set'
    };
  }
  
  // Validate each element
  for (let i = 0; i < value.length; i++) {
    const result = validateValueAgainstType(
      value[i], 
      typeSpec.elementType || { type: 'Any' },
      [...path, `{${i}}`]
    );
    if (!result.valid) {
      return result;
    }
  }
  
  return { valid: true, path };
}

function validateTupleType(value: unknown, typeSpec: TypeSpec, path: string[]): ValidationResult {
  if (!Array.isArray(value)) {
    return { 
      valid: false, 
      error: `Expected tuple but got ${getValueTypeDescription(value)}`,
      path,
      suggestion: 'Use tuple notation: (item1, item2, ...)'
    };
  }
  
  // Validate each element
  for (let i = 0; i < value.length; i++) {
    const result = validateValueAgainstType(
      value[i], 
      typeSpec.elementType || { type: 'Any' },
      [...path, `(${i})`]
    );
    if (!result.valid) {
      return result;
    }
  }
  
  return { valid: true, path };
}

// ===== ENHANCED SUGGESTION GENERATORS =====

function generateUnionTypeSuggestion(value: unknown, unionTypes: TypeSpec[]): string {
  // Find the closest matching type based on the value
  for (const type of unionTypes) {
    if (type.type === 'None' && (value === null || value === undefined)) {
      return 'None';
    }
    if (type.type === 'str' && typeof value === 'string') {
      return `"${value}"`;
    }
    if (type.type === 'int' && typeof value === 'number' && Number.isInteger(value)) {
      return String(value);
    }
    if (type.type === 'float' && typeof value === 'number') {
      return String(value);
    }
    if (type.type === 'bool' && typeof value === 'boolean') {
      return value ? 'True' : 'False';
    }
  }
  
  // Return the first type as fallback
  return formatTypeSpec(unionTypes[0]);
}

function generateIntSuggestion(value: unknown): string {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : String(Math.round(value));
  }
  if (typeof value === 'string') {
    const parsed = parseInt(value, 10);
    return isNaN(parsed) ? '42' : String(parsed);
  }
  if (typeof value === 'boolean') {
    return value ? '1' : '0';
  }
  return '42';
}

function generateFloatSuggestion(value: unknown): string {
  if (typeof value === 'number') {
    return String(value);
  }
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? '3.14' : String(parsed);
  }
  if (typeof value === 'boolean') {
    return value ? '1.0' : '0.0';
  }
  return '3.14';
}

function generateStrSuggestion(value: unknown): string {
  if (typeof value === 'string') {
    return `"${value}"`;
  }
  return `"${String(value)}"`;
}

function generateBoolSuggestion(value: unknown): string {
  if (typeof value === 'boolean') {
    return value ? 'True' : 'False';
  }
  if (typeof value === 'number') {
    return value !== 0 ? 'True' : 'False';
  }
  if (typeof value === 'string') {
    const lower = value.toLowerCase();
    if (['true', 'yes', '1'].includes(lower)) return 'True';
    if (['false', 'no', '0'].includes(lower)) return 'False';
  }
  return 'True';
}

function getValueTypeDescription(value: unknown): string {
  if (value === null || value === undefined) return 'None';
  if (Array.isArray(value)) return 'list';
  if (typeof value === 'object') return 'dict';
  if (typeof value === 'number') {
    return Number.isInteger(value) ? 'int' : 'float';
  }
  return typeof value;
}

// ===== ENHANCED TYPE INFERENCE =====

export function inferPythonTypeFromValue(value: unknown): TypeSpec {
  if (value === null || value === undefined) {
    return { type: 'None' };
  }
  
  // Handle primitive types
  if (typeof value === 'boolean') {
    return { type: 'bool' };
  }
  
  if (typeof value === 'number') {
    return Number.isInteger(value) ? { type: 'int' } : { type: 'float' };
  }
  
  if (typeof value === 'string') {
    return { type: 'str' };
  }
  
  // Handle arrays (lists/tuples)
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return { type: 'list', elementType: { type: 'Any' } };
    }
    
    // Analyze all elements to determine the most specific common type
    const elementTypes = value.map(inferPythonTypeFromValue);
    const commonType = findCommonType(elementTypes);
    
    return { type: 'list', elementType: commonType };
  }
  
  // Handle objects (dicts)
  if (typeof value === 'object') {
    const entries = Object.entries(value);
    if (entries.length === 0) {
      return { type: 'dict', keyType: { type: 'Any' }, valueType: { type: 'Any' } };
    }
    
    // Analyze keys and values
    const keyTypes = entries.map(([key]) => inferTypeFromString(key));
    const valueTypes = entries.map(([, val]) => inferPythonTypeFromValue(val));
    
    const commonKeyType = findCommonType(keyTypes);
    const commonValueType = findCommonType(valueTypes);
    
    return { 
      type: 'dict', 
      keyType: commonKeyType, 
      valueType: commonValueType 
    };
  }
  
  return { type: 'Any' };
}

export function findCommonType(types: TypeSpec[]): TypeSpec {
  if (types.length === 0) return { type: 'Any' };
  if (types.length === 1) return types[0];
  
  // Check if all types are identical
  const firstType = types[0];
  const allSame = types.every(t => deepTypeEquals(t, firstType));
  if (allSame) return firstType;
  
  // Check for numeric compatibility (int + float = float)
  const hasInt = types.some(t => t.type === 'int');
  const hasFloat = types.some(t => t.type === 'float');
  const allNumeric = types.every(t => t.type === 'int' || t.type === 'float');
  
  if (allNumeric && (hasInt || hasFloat)) {
    return hasFloat ? { type: 'float' } : { type: 'int' };
  }
  
  // Check for collection type compatibility
  const listTypes = types.filter(t => t.type === 'list');
  if (listTypes.length === types.length) {
    const elementTypes = listTypes.map(t => t.elementType).filter(Boolean) as TypeSpec[];
    return { type: 'list', elementType: findCommonType(elementTypes) };
  }
  
  const dictTypes = types.filter(t => t.type === 'dict');
  if (dictTypes.length === types.length) {
    const keyTypes = dictTypes.map(t => t.keyType).filter(Boolean) as TypeSpec[];
    const valueTypes = dictTypes.map(t => t.valueType).filter(Boolean) as TypeSpec[];
    return { 
      type: 'dict', 
      keyType: findCommonType(keyTypes), 
      valueType: findCommonType(valueTypes) 
    };
  }
  
  // If types are different, create a Union type
  const uniqueTypes = types.filter((type, index, arr) => 
    arr.findIndex(t => deepTypeEquals(t, type)) === index
  );
  
  if (uniqueTypes.length > 1) {
    return { type: 'Union', unionTypes: uniqueTypes };
  }
  
  return { type: 'Any' };
}

export function deepTypeEquals(type1: TypeSpec, type2: TypeSpec): boolean {
  if (type1.type !== type2.type) return false;
  
  if (type1.type === 'list') {
    return deepTypeEquals(type1.elementType || { type: 'Any' }, type2.elementType || { type: 'Any' });
  }
  
  if (type1.type === 'dict') {
    return deepTypeEquals(type1.keyType || { type: 'Any' }, type2.keyType || { type: 'Any' }) &&
           deepTypeEquals(type1.valueType || { type: 'Any' }, type2.valueType || { type: 'Any' });
  }
  
  if (type1.type === 'Union') {
    const unions1 = type1.unionTypes || [];
    const unions2 = type2.unionTypes || [];
    
    if (unions1.length !== unions2.length) return false;
    
    return unions1.every(u1 => unions2.some(u2 => deepTypeEquals(u1, u2)));
  }
  
  return true;
}

export function inferTypeFromString(str: string): TypeSpec {
  // Check for None
  if (/^(None|null|none)$/i.test(str)) {
    return { type: 'None' };
  }
  
  // Check for boolean
  if (/^(true|false|True|False)$/i.test(str)) {
    return { type: 'bool' };
  }
  
  // Check for integer
  if (/^-?\d+$/.test(str)) {
    return { type: 'int' };
  }
  
  // Check for float
  if (/^-?\d*\.\d+$/.test(str)) {
    return { type: 'float' };
  }
  
  // Default to string
  return { type: 'str' };
}

// ===== ENHANCED TYPE DETECTION =====

export function autoDetectTypeFromInput(inputValue: string): TypeDetectionResult {
  if (!inputValue || inputValue.trim() === '') {
    return { detected: 'None', annotation: 'None', confidence: 'high' };
  }
  
  const trimmed = inputValue.trim();
  
  // Handle primitive string patterns with confidence levels
  if (/^(None|null|none)$/i.test(trimmed)) {
    return { detected: 'None', annotation: 'None', confidence: 'high' };
  }
  
  if (/^(true|false|True|False)$/i.test(trimmed)) {
    return { detected: 'bool', annotation: 'bool', confidence: 'high' };
  }
  
  if (/^(yes|no|1|0)$/i.test(trimmed)) {
    return { detected: 'bool', annotation: 'bool', confidence: 'medium' };
  }
  
  if (/^-?\d+$/.test(trimmed)) {
    return { detected: 'int', annotation: 'int', confidence: 'high' };
  }
  
  if (/^-?\d*\.\d+([eE][+-]?\d+)?$/.test(trimmed)) {
    return { detected: 'float', annotation: 'float', confidence: 'high' };
  }
  
  // Try to parse as JSON for collections
  if ((trimmed.startsWith('[') && trimmed.endsWith(']')) ||
      (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('(') && trimmed.endsWith(')'))) {
    
    try {
      let parsed: unknown;
      
      // Handle tuple notation
      if (trimmed.startsWith('(') && trimmed.endsWith(')')) {
        const arrayStr = trimmed.replace(/^\(/, '[').replace(/\)$/, ']');
        parsed = JSON.parse(arrayStr);
        const inferredType = inferPythonTypeFromValue(parsed);
        return { 
          detected: 'tuple', 
          annotation: `Tuple[${formatTypeSpec(inferredType.elementType || { type: 'Any' })}]`,
          confidence: 'high'
        };
      }
      
      // Handle list/dict notation
      parsed = JSON.parse(trimmed);
      const inferredType = inferPythonTypeFromValue(parsed);
      return { 
        detected: inferredType.type, 
        annotation: formatTypeSpec(inferredType),
        confidence: 'high'
      };
      
    } catch {
      return { detected: 'invalid', annotation: 'invalid', confidence: 'high' };
    }
  }
  
  // Handle quoted strings
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
      (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return { detected: 'str', annotation: 'str', confidence: 'high' };
  }
  
  // Handle unquoted strings (lower confidence)
  if (/^[a-zA-Z_][a-zA-Z0-9_\s]*$/.test(trimmed)) {
    return { detected: 'str', annotation: 'str', confidence: 'medium' };
  }
  
  // Invalid input
  return { detected: 'invalid', annotation: 'invalid', confidence: 'high' };
}

export function autoDetectAndConvert(value: string): unknown {
  const typeInfo = autoDetectTypeFromInput(value);
  const typeHandler = pythonTypes[typeInfo.detected];
  
  if (typeHandler && typeHandler.convert) {
    try {
      return typeHandler.convert(value);
    } catch (error) {
      throw new Error(`Type conversion failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
  
  return value;
}

// ===== ENHANCED TYPE FORMATTING =====

export function formatTypeSpec(typeSpec: TypeSpec): string {
  if (!typeSpec) return 'Any';
  
  switch (typeSpec.type) {
    case 'Union':
      if (typeSpec.unionTypes) {
        const formatted = typeSpec.unionTypes.map(formatTypeSpec).join(' | ');
        return `Union[${formatted}]`;
      }
      return 'Union';
      
    case 'Optional':
      return `Optional[${formatTypeSpec(typeSpec.innerType || { type: 'Any' })}]`;
      
    case 'Literal':
      if (typeSpec.literalValues) {
        const values = typeSpec.literalValues.map(v => JSON.stringify(v)).join(', ');
        return `Literal[${values}]`;
      }
      return 'Literal';
      
    case 'list':
      return `List[${formatTypeSpec(typeSpec.elementType || { type: 'Any' })}]`;
      
    case 'dict':
      const keyType = formatTypeSpec(typeSpec.keyType || { type: 'Any' });
      const valueType = formatTypeSpec(typeSpec.valueType || { type: 'Any' });
      return `Dict[${keyType}, ${valueType}]`;
      
    case 'set':
      return `Set[${formatTypeSpec(typeSpec.elementType || { type: 'Any' })}]`;
      
    case 'tuple':
      return `Tuple[${formatTypeSpec(typeSpec.elementType || { type: 'Any' })}]`;
      
    default:
      return typeSpec.type;
  }
}

// ===== UTILITY FUNCTIONS =====

export function simplifyPythonType(typeStr: string): string {
  const typeSpec = parseTypeAnnotation(typeStr);
  return typeSpec.type;
}

export function getPlaceholderForType(typeStr: string): string {
  const simplified = simplifyPythonType(typeStr);
  return pythonTypes[simplified]?.placeholder || 'value';
}

export function formatValueForInput(value: unknown): string {
  if (value === null || value === undefined) return 'None';
  if (typeof value === 'boolean') return value ? 'True' : 'False';
  if (typeof value === 'string') return value; // Don't add quotes for display
  if (Array.isArray(value) || typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

export function getTypeExamples(typeStr: string): string[] {
  const simplified = simplifyPythonType(typeStr);
  return pythonTypes[simplified]?.examples || [];
}

export function getTypeDescription(typeStr: string): string {
  const simplified = simplifyPythonType(typeStr);
  return pythonTypes[simplified]?.description || 'Unknown type';
}

