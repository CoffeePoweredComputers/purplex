<template>
  <div class="smart-test-case-input">
    <!-- Function Parameters -->
    <div class="parameters-section">
      <label class="section-label">Function Parameters</label>
      <div v-if="functionParameters.length === 0" class="no-parameters">
        <span class="empty-state">No parameters detected. Check function signature.</span>
      </div>
      <div v-else class="parameters-container">
        <!-- Parameter grid header -->
        <div 
          class="parameters-grid-header"
          :style="{ '--param-count': functionParameters.length }"
        >
          <div 
            v-for="(param, paramIndex) in functionParameters" 
            :key="paramIndex" 
            class="parameter-header"
          >
            <span class="parameter-name">{{ param.name }}</span>
            <span class="parameter-type">{{ param.type }}</span>
          </div>
          <div class="actions-header">
            Actions
          </div>
        </div>
        
        <!-- Parameter input rows -->
        <div 
          v-for="(paramSet, setIndex) in parameterSets" 
          :key="setIndex" 
          class="parameter-row"
          :style="{ '--param-count': functionParameters.length }"
        >
          <div 
            v-for="(param, paramIndex) in functionParameters" 
            :key="paramIndex" 
            class="parameter-cell"
          >
            <div class="input-with-type">
              <input
                v-model="paramSet[paramIndex].value"
                @input="onParameterChange(setIndex, paramIndex)"
                type="text"
                :placeholder="getParameterPlaceholder(functionParameters[paramIndex].type)"
                class="smart-input"
                :class="{ 'error': paramSet[paramIndex].error }"
              />
              <div 
                class="type-indicator" 
                :class="getSimplifiedType(paramSet[paramIndex].detectedType)"
                :title="paramSet[paramIndex].detectedType"
              >
                {{ paramSet[paramIndex].detectedType }}
              </div>
            </div>
            <div v-if="paramSet[paramIndex].error" class="parameter-error">{{ paramSet[paramIndex].error }}</div>
            <div class="parameter-preview">{{ paramSet[paramIndex].preview }}</div>
          </div>
          
          <!-- Actions cell -->
          <div class="actions-cell">
            <button 
              v-if="parameterSets.length > 1"
              @click="removeParameterSet(setIndex)"
              class="remove-set-btn"
              title="Remove this input set"
            >
              ×
            </button>
          </div>
        </div>
        
        <!-- Add parameter set button -->
        <div class="add-parameter-set">
          <button 
            @click="addParameterSet" 
            :disabled="!canAddParameterSet"
            class="add-set-btn"
            :class="{ 'disabled': !canAddParameterSet }"
            :title="canAddParameterSetReason"
          >
            <span class="add-icon">+</span>
            <span v-if="canAddParameterSet">Add Input Set</span>
            <span v-else>{{ canAddParameterSetReason }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Expected Output -->
    <div class="output-section">
      <label class="section-label">Expected Output</label>
      <div class="input-with-type">
        <input
          v-model="expectedOutput.value"
          @input="onExpectedOutputChange"
          type="text"
          :placeholder="getParameterPlaceholder(returnType)"
          class="smart-input"
          :class="{ 'error': expectedOutput.error }"
        />
        <div 
          class="type-indicator" 
          :class="getSimplifiedType(expectedOutput.detectedType)"
          :title="expectedOutput.detectedType"
        >
          {{ expectedOutput.detectedType }}
        </div>
      </div>
      <div v-if="expectedOutput.error" class="parameter-error">{{ expectedOutput.error }}</div>
      <div class="parameter-preview">{{ expectedOutput.preview }}</div>
    </div>

    <!-- Function Call Preview -->
    <div class="preview-section">
      <label class="section-label">Function Call Preview</label>
      <div class="function-call-preview">
        <div 
          v-for="(paramSet, setIndex) in parameterSets" 
          :key="setIndex" 
          class="call-preview-item"
        >
          <div class="call-input">
            <span class="call-label">Call {{ setIndex + 1 }}:</span>
            <code class="function-call">{{ generateFunctionCall(setIndex) }}</code>
          </div>
          <div class="call-output">
            <span class="output-label">→</span>
            <code class="expected-result">{{ formatExpectedOutput() }}</code>
          </div>
        </div>
      </div>
    </div>

    <!-- Description -->
    <div class="description-section">
      <label class="section-label">Description (optional)</label>
      <input
        v-model="description"
        type="text"
        placeholder="Brief description of this test case"
        class="description-input"
      />
    </div>
  </div>
</template>

<script>
// Type detection and conversion utilities
const pythonTypes = {
  // Basic types
  'int': { 
    validate: /^-?\d+$/, 
    convert: (v) => parseInt(v),
    placeholder: '42'
  },
  'float': { 
    validate: /^-?\d*\.?\d+$/, 
    convert: (v) => parseFloat(v),
    placeholder: '3.14'
  },
  'str': { 
    validate: /.*/, 
    convert: (v) => {
      // Remove quotes if present
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
        return v.slice(1, -1);
      }
      return String(v);
    },
    placeholder: 'hello world'
  },
  'bool': { 
    validate: /^(true|false|True|False|yes|no|1|0)$/i, 
    convert: (v) => {
      const lower = v.toLowerCase();
      return lower === 'true' || lower === 'yes' || lower === '1';
    },
    placeholder: 'true'
  },
  
  // Collections
  'list': { 
    validate: /^\[.*\]$/, 
    convert: (v) => JSON.parse(v),
    placeholder: '[1, 2, 3]'
  },
  'dict': { 
    validate: /^\{.*\}$/, 
    convert: (v) => JSON.parse(v),
    placeholder: '{"key": "value"}'
  },
  'tuple': { 
    validate: /^\(.*\)$/, 
    convert: (v) => {
      // Convert tuple notation to array
      const arrayStr = v.replace(/^\(/, '[').replace(/\)$/, ']');
      return JSON.parse(arrayStr);
    },
    placeholder: '(1, 2, 3)'
  },
  'set': { 
    validate: /^\{.*\}$/, 
    convert: (v) => {
      // Sets in JSON are just arrays
      const parsed = JSON.parse(v);
      return Array.isArray(parsed) ? parsed : Array.from(new Set(Object.values(parsed)));
    },
    placeholder: '{1, 2, 3}'
  },
  
  // Special
  'None': { 
    validate: /^(None|null|none)$/i, 
    convert: () => null,
    placeholder: 'None'
  },
  'Any': { 
    validate: /.*/, 
    convert: (v) => autoDetectAndConvert(v),
    placeholder: 'any value'
  }
};

// Recursively validate a value against a type specification
function validateValueAgainstType(value, typeSpec, path = []) {
  // Handle Any type - always valid
  if (typeSpec.type === 'Any') {
    return { valid: true };
  }
  
  // Handle Optional type
  if (typeSpec.type === 'Optional') {
    if (value === null || value === undefined) {
      return { valid: true };
    }
    return validateValueAgainstType(value, typeSpec.innerType, path);
  }
  
  // Handle None type
  if (typeSpec.type === 'None') {
    if (value === null || value === undefined) {
      return { valid: true };
    }
    return { 
      valid: false, 
      error: `Expected None but got ${typeof value}`,
      path 
    };
  }
  
  // Handle primitive types
  if (['int', 'float', 'str', 'bool'].includes(typeSpec.type)) {
    const actualType = typeof value;
    
    switch (typeSpec.type) {
      case 'int':
        if (typeof value === 'number' && Number.isInteger(value)) {
          return { valid: true };
        }
        return { 
          valid: false, 
          error: `Expected int but got ${actualType === 'number' ? 'float' : actualType}`,
          path 
        };
        
      case 'float':
        if (typeof value === 'number') {
          return { valid: true };
        }
        return { 
          valid: false, 
          error: `Expected float but got ${actualType}`,
          path 
        };
        
      case 'str':
        if (typeof value === 'string') {
          return { valid: true };
        }
        return { 
          valid: false, 
          error: `Expected str but got ${actualType}`,
          path 
        };
        
      case 'bool':
        if (typeof value === 'boolean') {
          return { valid: true };
        }
        return { 
          valid: false, 
          error: `Expected bool but got ${actualType}`,
          path 
        };
    }
  }
  
  // Handle list type
  if (typeSpec.type === 'list') {
    if (!Array.isArray(value)) {
      return { 
        valid: false, 
        error: `Expected list but got ${typeof value}`,
        path 
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
        return result; // Return first error
      }
    }
    return { valid: true };
  }
  
  // Handle dict type
  if (typeSpec.type === 'dict') {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
      return { 
        valid: false, 
        error: `Expected dict but got ${Array.isArray(value) ? 'list' : typeof value}`,
        path 
      };
    }
    
    // Validate each key-value pair
    for (const [key, val] of Object.entries(value)) {
      // For dict keys, try to convert them to the expected type
      let convertedKey = key;
      if (typeSpec.keyType && typeSpec.keyType.type !== 'str' && typeSpec.keyType.type !== 'Any') {
        try {
          // Try to convert string key to expected type
          if (typeSpec.keyType.type === 'int') {
            convertedKey = parseInt(key);
            if (isNaN(convertedKey) || !Number.isInteger(convertedKey)) {
              return {
                valid: false,
                error: `Expected int key but "${key}" cannot be converted to integer`,
                path: [...path, `key "${key}"`]
              };
            }
          } else if (typeSpec.keyType.type === 'float') {
            convertedKey = parseFloat(key);
            if (isNaN(convertedKey)) {
              return {
                valid: false,
                error: `Expected float key but "${key}" cannot be converted to float`,
                path: [...path, `key "${key}"`]
              };
            }
          }
          // For other types, validate as-is
          else {
            const keyResult = validateValueAgainstType(
              key,
              typeSpec.keyType,
              [...path, `key "${key}"`]
            );
            if (!keyResult.valid) {
              return keyResult;
            }
          }
        } catch (error) {
          return {
            valid: false,
            error: `Invalid key "${key}": ${error.message}`,
            path: [...path, `key "${key}"`]
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
    return { valid: true };
  }
  
  // Handle set type (represented as array in JSON)
  if (typeSpec.type === 'set') {
    if (!Array.isArray(value)) {
      return { 
        valid: false, 
        error: `Expected set but got ${typeof value}`,
        path 
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
    return { valid: true };
  }
  
  // Handle tuple type
  if (typeSpec.type === 'tuple') {
    if (!Array.isArray(value)) {
      return { 
        valid: false, 
        error: `Expected tuple but got ${typeof value}`,
        path 
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
    return { valid: true };
  }
  
  // Unknown type
  return { valid: true };
}

// Advanced Python type inference from actual values
function inferPythonTypeFromValue(value) {
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
    
    // Analyze keys - try to infer if they're really integers, floats, etc.
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

// Find the most specific common type among a list of types
function findCommonType(types) {
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
    const elementTypes = listTypes.map(t => t.elementType);
    return { type: 'list', elementType: findCommonType(elementTypes) };
  }
  
  const dictTypes = types.filter(t => t.type === 'dict');
  if (dictTypes.length === types.length) {
    const keyTypes = dictTypes.map(t => t.keyType);
    const valueTypes = dictTypes.map(t => t.valueType);
    return { 
      type: 'dict', 
      keyType: findCommonType(keyTypes), 
      valueType: findCommonType(valueTypes) 
    };
  }
  
  // If no common type found, return Any
  return { type: 'Any' };
}

// Deep equality check for type specs
function deepTypeEquals(type1, type2) {
  if (type1.type !== type2.type) return false;
  
  if (type1.type === 'list') {
    return deepTypeEquals(type1.elementType || { type: 'Any' }, type2.elementType || { type: 'Any' });
  }
  
  if (type1.type === 'dict') {
    return deepTypeEquals(type1.keyType || { type: 'Any' }, type2.keyType || { type: 'Any' }) &&
           deepTypeEquals(type1.valueType || { type: 'Any' }, type2.valueType || { type: 'Any' });
  }
  
  return true;
}

// Infer type from string value (for dict keys or string literals)
function inferTypeFromString(str) {
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

// Auto-detect type from input string and infer full type annotation
function autoDetectTypeFromInput(inputValue) {
  if (!inputValue || inputValue.trim() === '') {
    return { detected: 'None', annotation: 'None' };
  }
  
  const trimmed = inputValue.trim();
  
  // Handle primitive string patterns
  if (/^(None|null|none)$/i.test(trimmed)) {
    return { detected: 'None', annotation: 'None' };
  }
  
  if (/^(true|false|True|False|yes|no|1|0)$/i.test(trimmed)) {
    return { detected: 'bool', annotation: 'bool' };
  }
  
  if (/^-?\d+$/.test(trimmed)) {
    return { detected: 'int', annotation: 'int' };
  }
  
  if (/^-?\d*\.\d+$/.test(trimmed)) {
    return { detected: 'float', annotation: 'float' };
  }
  
  // Try to parse as JSON for collections
  if ((trimmed.startsWith('[') && trimmed.endsWith(']')) ||
      (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('(') && trimmed.endsWith(')'))) {
    
    try {
      let parsed;
      
      // Handle tuple notation
      if (trimmed.startsWith('(') && trimmed.endsWith(')')) {
        const arrayStr = trimmed.replace(/^\(/, '[').replace(/\)$/, ']');
        parsed = JSON.parse(arrayStr);
        const inferredType = inferPythonTypeFromValue(parsed);
        return { 
          detected: 'tuple', 
          annotation: `Tuple[${formatTypeSpec(inferredType.elementType)}]`
        };
      }
      
      // Handle list/dict notation
      parsed = JSON.parse(trimmed);
      const inferredType = inferPythonTypeFromValue(parsed);
      return { 
        detected: inferredType.type, 
        annotation: formatTypeSpec(inferredType) 
      };
      
    } catch {
      return { detected: 'invalid', annotation: 'invalid' };
    }
  }
  
  // Handle quoted strings
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
      (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return { detected: 'str', annotation: 'str' };
  }
  
  // Handle unquoted identifiers
  if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(trimmed)) {
    return { detected: 'str', annotation: 'str' };
  }
  
  // Invalid input
  return { detected: 'invalid', annotation: 'invalid' };
}

function autoDetectAndConvert(value) {
  const typeInfo = autoDetectTypeFromInput(value);
  const typeHandler = pythonTypes[typeInfo.detected];
  if (typeHandler && typeHandler.convert) {
    try {
      return typeHandler.convert(value);
    } catch {
      return value;
    }
  }
  return value;
}

// Parse function signature
function parseFunctionSignature(signature) {
  // Examples:
  // "def is_anagram(str1: str, str2: str) -> bool:"
  // "def two_sum(nums: List[int], target: int) -> List[int]:"
  // "def group_by_length(words: List[str]) -> Dict[int, List[str]]:"
  
  const regex = /def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*(.+?))?:/;
  const match = signature.match(regex);
  
  if (!match) return null;
  
  const [_, functionName, params, returnType] = match;
  const parameters = parseParameters(params);
  
  return {
    functionName,
    parameters,
    returnType: returnType?.trim() || 'Any'
  };
}

function parseParameters(paramsStr) {
  if (!paramsStr.trim()) return [];
  
  const params = [];
  const paramRegex = /(\w+)\s*:\s*([^,]+)/g;
  let match;
  
  while ((match = paramRegex.exec(paramsStr)) !== null) {
    params.push({
      name: match[1],
      type: match[2].trim(),
      pythonType: simplifyPythonType(match[2].trim())
    });
  }
  
  // Handle parameters without type annotations
  if (params.length === 0) {
    // Simple split by comma for untyped parameters
    const simpleParams = paramsStr.split(',').map(p => p.trim());
    simpleParams.forEach(param => {
      if (param) {
        params.push({
          name: param,
          type: 'Any',
          pythonType: 'Any'
        });
      }
    });
  }
  
  return params;
}

// Parse Python type annotation into structured format
function parseTypeAnnotation(typeStr) {
  typeStr = typeStr.trim();
  
  // Handle Optional[T] by converting to T or None
  if (typeStr.startsWith('Optional[') && typeStr.endsWith(']')) {
    const inner = typeStr.slice(9, -1);
    return { type: 'Optional', innerType: parseTypeAnnotation(inner) };
  }
  
  // Handle List[T]
  if ((typeStr.startsWith('List[') || typeStr.startsWith('list[')) && typeStr.endsWith(']')) {
    const start = typeStr.indexOf('[') + 1;
    const inner = typeStr.slice(start, -1);
    return { type: 'list', elementType: parseTypeAnnotation(inner) };
  }
  
  // Handle Dict[K, V]
  if ((typeStr.startsWith('Dict[') || typeStr.startsWith('dict[')) && typeStr.endsWith(']')) {
    const start = typeStr.indexOf('[') + 1;
    const inner = typeStr.slice(start, -1);
    
    // Find the comma that separates key and value types
    let depth = 0;
    let commaIndex = -1;
    for (let i = 0; i < inner.length; i++) {
      if (inner[i] === '[') depth++;
      else if (inner[i] === ']') depth--;
      else if (inner[i] === ',' && depth === 0) {
        commaIndex = i;
        break;
      }
    }
    
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
  
  // Handle Set[T]
  if ((typeStr.startsWith('Set[') || typeStr.startsWith('set[')) && typeStr.endsWith(']')) {
    const start = typeStr.indexOf('[') + 1;
    const inner = typeStr.slice(start, -1);
    return { type: 'set', elementType: parseTypeAnnotation(inner) };
  }
  
  // Handle Tuple[T, ...]
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

// Format type spec back to readable string
function formatTypeSpec(typeSpec) {
  if (!typeSpec) return 'Any';
  
  switch (typeSpec.type) {
    case 'Optional':
      return `Optional[${formatTypeSpec(typeSpec.innerType)}]`;
    case 'list':
      return `List[${formatTypeSpec(typeSpec.elementType)}]`;
    case 'dict':
      return `Dict[${formatTypeSpec(typeSpec.keyType)}, ${formatTypeSpec(typeSpec.valueType)}]`;
    case 'set':
      return `Set[${formatTypeSpec(typeSpec.elementType)}]`;
    case 'tuple':
      return `Tuple[${formatTypeSpec(typeSpec.elementType)}]`;
    default:
      return typeSpec.type;
  }
}

// Simplify type spec for basic validation (backward compatibility)
function simplifyPythonType(typeStr) {
  const typeSpec = parseTypeAnnotation(typeStr);
  return typeSpec.type;
}

export default {
  name: 'SmartTestCaseInput',
  props: {
    functionSignature: {
      type: String,
      required: true
    },
    initialInputs: {
      type: Array,
      default: () => []
    },
    initialExpectedOutput: {
      default: null
    },
    initialDescription: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      functionParameters: [],
      parameterSets: [], // Array of parameter sets, each containing parameter values
      expectedOutput: {
        value: '',
        detectedType: 'Any',
        preview: '',
        error: null
      },
      returnType: 'Any',
      returnTypeSpec: { type: 'Any' },
      description: '',
      parsedSignature: null
    };
  },
  created() {
    this.parseSignature();
    this.initializeValues();
  },
  watch: {
    functionSignature() {
      this.parseSignature();
      this.initializeValues();
    }
  },
  methods: {
    parseSignature() {
      this.parsedSignature = parseFunctionSignature(this.functionSignature);
      if (!this.parsedSignature) {
        console.error('Failed to parse function signature:', this.functionSignature);
        return;
      }
      
      // Initialize parameters with parsed type specs
      this.functionParameters = this.parsedSignature.parameters.map((param, index) => ({
        name: param.name,
        type: param.type,
        pythonType: param.pythonType,
        typeSpec: parseTypeAnnotation(param.type)
      }));
      
      // Initialize with one parameter set if empty
      if (this.parameterSets.length === 0) {
        this.addParameterSet();
      }
      
      this.returnType = simplifyPythonType(this.parsedSignature.returnType);
      this.returnTypeSpec = parseTypeAnnotation(this.parsedSignature.returnType);
    },
    
    initializeValues() {
      // Initialize with any provided values
      if (this.initialInputs && this.initialInputs.length > 0) {
        // Ensure we have at least one parameter set
        if (this.parameterSets.length === 0) {
          this.addParameterSet();
        }
        
        this.initialInputs.forEach((value, index) => {
          if (this.parameterSets[0][index]) {
            // Convert value to string for display
            this.parameterSets[0][index].value = this.formatValueForInput(value);
            this.onParameterChange(0, index);
          }
        });
      }
      
      if (this.initialExpectedOutput !== null) {
        this.expectedOutput.value = this.formatValueForInput(this.initialExpectedOutput);
        this.onExpectedOutputChange();
      }
      
      this.description = this.initialDescription;
    },
    
    formatValueForInput(value) {
      // Convert a JavaScript value to string for input display
      if (value === null) return 'None';
      if (typeof value === 'string') return value;
      if (typeof value === 'boolean') return value.toString();
      if (Array.isArray(value) || typeof value === 'object') {
        return JSON.stringify(value);
      }
      return String(value);
    },
    
    onParameterChange(setIndex, paramIndex) {
      const param = this.parameterSets[setIndex][paramIndex];
      this.detectAndValidateType(param);
      this.emitChange();
    },
    
    onExpectedOutputChange() {
      this.detectAndValidateType(this.expectedOutput);
      this.emitChange();
    },
    
    detectAndValidateType(field) {
      if (!field.value) {
        field.detectedType = field.pythonType || 'Any';
        field.preview = '';
        field.error = null;
        return;
      }
      
      // Use the new advanced type detection
      const typeInfo = autoDetectTypeFromInput(field.value);
      
      // Handle invalid syntax
      if (typeInfo.detected === 'invalid') {
        field.detectedType = 'invalid';
        field.error = this.getInvalidTypeError(field.value);
        field.preview = '';
        return;
      }
      
      // Set the detected type annotation (shows full type like "Dict[int, List[str]]")
      field.detectedType = typeInfo.annotation;
      
      // Try to parse and convert the value
      try {
        const converted = this.parseAndConvertValue(field.value, typeInfo.detected);
        
        // If we have an expected type spec, validate against it
        const expectedTypeSpec = field.typeSpec || this.returnTypeSpec;
        if (expectedTypeSpec && expectedTypeSpec.type !== 'Any') {
          const validationResult = validateValueAgainstType(converted, expectedTypeSpec);
          if (!validationResult.valid) {
            const pathStr = validationResult.path.length > 0 ? ` at ${validationResult.path.join('')}` : '';
            field.error = `${validationResult.error}${pathStr}`;
            field.preview = '';
            return;
          }
        }
        
        // Show success with preview
        field.preview = this.formatPreview(converted, typeInfo.annotation);
        field.error = null;
        
      } catch (error) {
        field.error = `Parse error: ${error.message}`;
        field.preview = '';
      }
    },
    
    parseAndConvertValue(value, detectedType) {
      // Handle type spec objects
      if (typeof detectedType === 'object' && detectedType.type) {
        const simpleType = detectedType.type;
        const typeHandler = pythonTypes[simpleType];
        if (typeHandler) {
          return typeHandler.convert(value);
        }
      }
      
      // Handle simple type strings
      const typeHandler = pythonTypes[detectedType];
      if (typeHandler) {
        return typeHandler.convert(value);
      }
      
      throw new Error(`Unknown type: ${detectedType}`);
    },
    
    getInvalidTypeError(value) {
      // Provide helpful error messages based on the input pattern
      if (value.startsWith('[') || value.endsWith(']')) {
        return 'Invalid list syntax. Example: [1, 2, 3]';
      }
      if (value.startsWith('{') || value.endsWith('}')) {
        return 'Invalid dict syntax. Example: {"key": "value"}';
      }
      if (value.startsWith('(') || value.endsWith(')')) {
        return 'Invalid tuple syntax. Example: (1, 2, 3)';
      }
      if (value.includes(',')) {
        return 'Invalid format. Did you mean to create a list? Use square brackets: [1, 2, 3]';
      }
      return 'Invalid input format. Please enter a valid Python value.';
    },
    
    formatPreview(value, type) {
      if (value === null) return '→ None';
      if (type === 'str') return `→ "${value}"`;
      if (type === 'bool') return `→ ${value ? 'True' : 'False'}`;
      if (Array.isArray(value)) return `→ ${JSON.stringify(value)}`;
      if (typeof value === 'object') return `→ ${JSON.stringify(value)}`;
      return `→ ${value}`;
    },
    
    getParameterPlaceholder(type) {
      const pythonType = simplifyPythonType(type);
      return pythonTypes[pythonType]?.placeholder || 'Enter value';
    },
    
    getSimplifiedType(type) {
      // Handle complex type strings like "Dict[int, List[str]]"
      const baseType = typeof type === 'string' && type.includes('[') 
        ? type.split('[')[0].toLowerCase() 
        : type;
      
      // Return CSS class based on type category
      if (['int', 'float'].includes(baseType)) return 'type-number';
      if (baseType === 'str') return 'type-string';
      if (baseType === 'bool') return 'type-boolean';
      if (['list', 'dict', 'tuple', 'set'].includes(baseType)) return 'type-collection';
      if (baseType === 'none') return 'type-none';
      if (baseType === 'invalid') return 'type-invalid';
      if (baseType === 'optional') return 'type-optional';
      return 'type-any';
    },
    
    
    getTestCaseData() {
      // Don't return data if there are validation errors
      if (this.hasErrors()) {
        return {
          inputs: [],
          expected_output: null,
          description: this.description,
          hasErrors: true
        };
      }
      
      // For now, return the first parameter set as inputs
      // TODO: Extend backend to support multiple parameter sets
      const firstParameterSet = this.parameterSets[0] || [];
      
      // Convert the smart inputs to the format expected by the backend
      const inputs = firstParameterSet.map(param => {
        if (!param.value) return null;
        if (param.detectedType === 'invalid') return null;
        
        const typeInfo = autoDetectTypeFromInput(param.value);
        const typeHandler = pythonTypes[typeInfo.detected];
        if (typeHandler) {
          try {
            return typeHandler.convert(param.value);
          } catch {
            return null;
          }
        }
        return null;
      });
      
      let expectedOutput = null;
      if (this.expectedOutput.value && this.expectedOutput.detectedType !== 'invalid') {
        const typeInfo = autoDetectTypeFromInput(this.expectedOutput.value);
        const typeHandler = pythonTypes[typeInfo.detected];
        if (typeHandler) {
          try {
            expectedOutput = typeHandler.convert(this.expectedOutput.value);
          } catch {
            expectedOutput = null;
          }
        }
      }
      
      return {
        inputs,
        expected_output: expectedOutput,
        description: this.description,
        hasErrors: false
      };
    },
    
    emitChange() {
      // Emit the test case data whenever something changes
      this.$emit('change', this.getTestCaseData());
    },
    
    hasErrors() {
      // Check if any parameters in any set or expected output have errors
      const hasParameterErrors = this.parameterSets.some(paramSet => 
        paramSet.some(p => p.error)
      );
      return hasParameterErrors || !!this.expectedOutput.error;
    },
    
    validate() {
      // Validate all inputs
      let isValid = true;
      
      this.parameterSets.forEach((paramSet, setIndex) => {
        paramSet.forEach((param, paramIndex) => {
          if (!param.value && this.functionParameters[paramIndex].pythonType !== 'None') {
            param.error = 'This parameter is required';
            isValid = false;
          } else {
            this.detectAndValidateType(param);
            if (param.error) isValid = false;
          }
        });
      });
      
      if (!this.expectedOutput.value && this.returnType !== 'None') {
        this.expectedOutput.error = 'Expected output is required';
        isValid = false;
      } else {
        this.detectAndValidateType(this.expectedOutput);
        if (this.expectedOutput.error) isValid = false;
      }
      
      return isValid;
    },
    
    addParameterSet() {
      // Create a new parameter set with empty values for each parameter
      const newParameterSet = this.functionParameters.map((param, index) => ({
        value: '',
        detectedType: param.pythonType,
        preview: '',
        error: null,
        typeSpec: param.typeSpec
      }));
      
      this.parameterSets.push(newParameterSet);
      this.emitChange();
    },
    
    removeParameterSet(setIndex) {
      if (this.parameterSets.length > 1) {
        this.parameterSets.splice(setIndex, 1);
        this.emitChange();
      }
    },
    
    generateFunctionCall(setIndex) {
      if (!this.parsedSignature || !this.parameterSets[setIndex]) {
        return '';
      }
      
      const functionName = this.parsedSignature.functionName;
      const paramSet = this.parameterSets[setIndex];
      
      const args = paramSet.map((param, index) => {
        if (!param.value) return 'None';
        
        // Format the value for display in function call
        try {
          const typeInfo = autoDetectTypeFromInput(param.value);
          if (typeInfo.detected === 'str') {
            // Show strings with quotes
            const converted = this.parseAndConvertValue(param.value, typeInfo.detected);
            return JSON.stringify(converted);
          } else {
            return param.value;
          }
        } catch {
          return param.value;
        }
      }).join(', ');
      
      return `${functionName}(${args})`;
    },
    
    formatExpectedOutput() {
      if (!this.expectedOutput.value) {
        return 'None';
      }
      
      try {
        const typeInfo = autoDetectTypeFromInput(this.expectedOutput.value);
        if (typeInfo.detected === 'str') {
          const converted = this.parseAndConvertValue(this.expectedOutput.value, typeInfo.detected);
          return JSON.stringify(converted);
        } else {
          return this.expectedOutput.value;
        }
      } catch {
        return this.expectedOutput.value;
      }
    },
    
    canAddParameterSet() {
      // Allow unlimited parameter sets for now
      // Could add limits based on performance or UI considerations
      return true;
    },
    
    canAddParameterSetReason() {
      if (!this.canAddParameterSet) {
        return 'Maximum number of input sets reached';
      }
      return 'Add another set of input parameters';
    }
  }
};
</script>

<style scoped>
.smart-test-case-input {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.section-label {
  display: block;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.parameters-section,
.output-section,
.description-section {
  background: var(--color-bg-hover);
  padding: var(--spacing-lg);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-bg-border);
}

.no-parameters {
  text-align: center;
  padding: var(--spacing-xl);
}

.empty-state {
  color: var(--color-text-muted);
  font-style: italic;
}

.parameters-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.parameter-input {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.parameter-label {
  font-weight: 500;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.input-with-type {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  position: relative;
}

.smart-input {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-family: 'Monaco', 'Consolas', monospace;
  transition: var(--transition-fast);
}

.smart-input:focus {
  outline: none;
  border-color: var(--color-primary);
  background: var(--color-bg);
}

.smart-input.error {
  border-color: var(--color-error);
}

.type-indicator {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-xs);
  font-weight: 600;
  letter-spacing: 0.5px;
  white-space: nowrap;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: 'Monaco', 'Consolas', monospace;
  text-transform: none;
}

.type-number {
  background: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

.type-string {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.type-boolean {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.type-collection {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
}

.type-none {
  background: var(--color-bg-muted);
  color: var(--color-text-muted);
  border: 1px solid var(--color-bg-border);
}

.type-any {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.type-invalid {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.type-optional {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.parameter-error {
  color: var(--color-error);
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-xs);
}

.parameter-preview {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-family: 'Monaco', 'Consolas', monospace;
  margin-top: var(--spacing-xs);
}

.description-input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-fast);
}

.description-input:focus {
  outline: none;
  border-color: var(--color-primary);
  background: var(--color-bg);
}

/* Multiple Parameter Sets - Grid Layout */
.parameters-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.parameters-grid-header {
  display: grid;
  grid-template-columns: repeat(var(--param-count, 1), 1fr) auto;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base) var(--radius-base) 0 0;
  border-bottom: none;
}

.parameter-header {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  text-align: center;
}

.parameter-name {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.parameter-type {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-bg-hover);
  padding: var(--spacing-xs);
  border-radius: var(--radius-xs);
  border: 1px solid var(--color-bg-border);
}

.actions-header {
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.parameter-row {
  display: grid;
  grid-template-columns: repeat(var(--param-count, 1), 1fr) auto;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--color-bg-hover);
  border: 2px solid var(--color-bg-border);
  border-top: none;
  transition: var(--transition-fast);
}

.parameter-row:hover {
  background: var(--color-bg-panel);
  border-color: var(--color-primary);
}

.parameter-row:last-of-type {
  border-radius: 0 0 var(--radius-base) var(--radius-base);
}

.parameter-cell {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.actions-cell {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: var(--spacing-xs);
}

.remove-set-btn {
  background: var(--color-error-bg);
  border: 1px solid var(--color-error);
  color: var(--color-error);
  border-radius: var(--radius-circle);
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  transition: var(--transition-fast);
}

.remove-set-btn:hover {
  background: var(--color-error);
  color: var(--color-text-primary);
  transform: scale(1.1);
}

.add-parameter-set {
  display: flex;
  justify-content: center;
  margin-top: var(--spacing-lg);
}

.add-set-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  width: 100%;
  background: var(--color-bg-panel);
  border: 2px dashed var(--color-bg-border);
  color: var(--color-text-secondary);
  border-radius: var(--radius-base);
  padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer;
  transition: var(--transition-fast);
  font-weight: 500;
  min-height: 48px;
}

.add-set-btn:hover:not(.disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-bg);
}

.add-set-btn.disabled {
  background: var(--color-bg-muted);
  border-color: var(--color-bg-border);
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.6;
}

.add-set-btn.disabled:hover {
  transform: none;
}

.add-icon {
  font-size: var(--font-size-lg);
  font-weight: bold;
}

/* Function Call Preview Section */
.preview-section {
  background: var(--color-bg-hover);
  padding: var(--spacing-lg);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-bg-border);
  margin-top: var(--spacing-md);
}

.function-call-preview {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.call-preview-item {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-bg-border);
}

.call-input,
.call-output {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.call-label,
.output-label {
  font-weight: 500;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  min-width: fit-content;
}

.output-label {
  font-size: var(--font-size-lg);
  color: var(--color-primary);
}

.function-call,
.expected-result {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: var(--font-size-sm);
  background: var(--color-bg-hover);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  border: 1px solid var(--color-bg-border);
  color: var(--color-text-primary);
  word-break: break-all;
}

.function-call {
  color: var(--color-info);
}

.expected-result {
  color: var(--color-success);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .input-with-type {
    flex-wrap: wrap;
  }
  
  .type-indicator {
    order: -1;
    width: 100%;
    text-align: center;
    margin-bottom: var(--spacing-sm);
  }
  
  .parameters-grid-header,
  .parameter-row {
    grid-template-columns: 1fr;
    gap: var(--spacing-sm);
  }
  
  .actions-header,
  .actions-cell {
    display: none;
  }
  
  .parameter-header {
    text-align: left;
  }
  
  .call-preview-item {
    grid-template-columns: 1fr;
    gap: var(--spacing-sm);
    text-align: center;
  }
  
  .remove-set-btn {
    position: absolute;
    top: var(--spacing-xs);
    right: var(--spacing-xs);
  }
  
  .parameter-row {
    position: relative;
  }
  
  .function-call,
  .expected-result {
    word-break: break-word;
  }
}
</style>