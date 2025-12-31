/**
 * useFunctionSignature - Parses Python function signatures.
 *
 * This composable handles parsing function signatures to extract:
 * - Function name
 * - Parameter names and types
 * - Return type
 *
 * Used for test case input field generation and type validation.
 */

import { type DeepReadonly, readonly, type Ref, ref } from 'vue';
import { parseTypeAnnotation } from '@/utils/typeSystem';

// ===== TYPES =====

export interface TypeSpec {
  type: string;
  elementType?: string;
  keyType?: string;
  valueType?: string;
}

export interface FunctionParameter {
  name: string;
  type: string;
  simplifiedType: string;
  typeSpec: TypeSpec;
}

export interface UseFunctionSignatureReturn {
  /** Parsed function parameters */
  functionParameters: DeepReadonly<Ref<FunctionParameter[]>>;
  /** Return type string */
  returnType: Ref<string>;
  /** Parsed return type spec */
  returnTypeSpec: Ref<TypeSpec>;
  /** Parse a function signature string */
  parse: (signature: string) => void;
  /** Get the number of parameters */
  getParameterCount: () => number;
  /** Get placeholder text for a parameter type */
  getParameterPlaceholder: (type: string) => string;
  /** Extract function name from code */
  extractFunctionName: (code: string) => string;
  /** Extract full function signature from code */
  extractSignature: (code: string) => string;
  /** Reset to initial state */
  reset: () => void;
}

// ===== COMPOSABLE =====

export const useFunctionSignature = (): UseFunctionSignatureReturn => {
  const functionParameters = ref<FunctionParameter[]>([]);
  const returnType = ref<string>('Any');
  const returnTypeSpec = ref<TypeSpec>({ type: 'Any' });

  /**
   * Parse parameter string into parameter objects
   */
  const parseParameters = (paramsStr: string): FunctionParameter[] => {
    if (!paramsStr.trim()) {return [];}

    const params: FunctionParameter[] = [];

    // Handle typed parameters: param: type
    const paramRegex = /(\w+)\s*:\s*([^,]+)/g;
    let match;

    while ((match = paramRegex.exec(paramsStr)) !== null) {
      const typeStr = match[2].trim();
      params.push({
        name: match[1],
        type: typeStr,
        simplifiedType: typeStr.toLowerCase().split('[')[0],
        typeSpec: parseTypeAnnotation(typeStr),
      });
    }

    // Handle untyped parameters if no typed ones found
    if (params.length === 0) {
      const simpleParams = paramsStr.split(',').map(p => p.trim()).filter(p => p);
      simpleParams.forEach(param => {
        params.push({
          name: param,
          type: 'Any',
          simplifiedType: 'any',
          typeSpec: { type: 'Any' },
        });
      });
    }

    return params;
  };

  /**
   * Parse function signature to extract parameters and return type.
   * Pattern: def func_name(param1: type1, param2: type2) -> return_type:
   */
  const parse = (signature: string): void => {
    if (!signature) {
      functionParameters.value = [];
      returnType.value = 'Any';
      returnTypeSpec.value = { type: 'Any' };
      return;
    }

    // Parse function signature pattern
    const regex = /def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*(.+?))?:/;
    const match = signature.match(regex);

    if (!match) {
      functionParameters.value = [];
      returnType.value = 'Any';
      returnTypeSpec.value = { type: 'Any' };
      return;
    }

    const [, , paramsStr, returnTypeStr] = match;

    // Parse parameters with enhanced type specs
    functionParameters.value = parseParameters(paramsStr || '');
    returnType.value = returnTypeStr?.trim() || 'Any';
    returnTypeSpec.value = parseTypeAnnotation(returnType.value);
  };

  /**
   * Get the number of parameters (minimum 1 for display purposes)
   */
  const getParameterCount = (): number => {
    return functionParameters.value.length || 1;
  };

  /**
   * Get placeholder text for a parameter type
   */
  const getParameterPlaceholder = (type: string): string => {
    const lowerType = type.toLowerCase();

    if (lowerType.includes('str')) {return '"example"';}
    if (lowerType.includes('int')) {return '42';}
    if (lowerType.includes('float')) {return '3.14';}
    if (lowerType.includes('bool')) {return 'True';}
    if (lowerType.includes('list')) {return '[1, 2, 3]';}
    if (lowerType.includes('dict')) {return '{"key": "value"}';}
    if (lowerType.includes('tuple')) {return '(1, 2)';}
    if (lowerType.includes('set')) {return '{1, 2, 3}';}
    if (lowerType === 'none') {return 'None';}

    return 'value';
  };

  /**
   * Extract function name from code
   */
  const extractFunctionName = (code: string): string => {
    if (!code) {return '';}

    const functionNameRegex = /def\s+(\w+)\s*\(/;
    const match = code.match(functionNameRegex);
    return match ? match[1] : '';
  };

  /**
   * Extract full function signature from code
   */
  const extractSignature = (code: string): string => {
    if (!code) {return '';}

    // Match the full function definition line including type hints
    const signatureRegex = /def\s+\w+\s*\([^)]*\)(?:\s*->\s*[^:]+)?:/;
    const match = code.match(signatureRegex);
    return match ? match[0] : '';
  };

  /**
   * Reset to initial state
   */
  const reset = (): void => {
    functionParameters.value = [];
    returnType.value = 'Any';
    returnTypeSpec.value = { type: 'Any' };
  };

  return {
    functionParameters: readonly(functionParameters),
    returnType,
    returnTypeSpec,
    parse,
    getParameterCount,
    getParameterPlaceholder,
    extractFunctionName,
    extractSignature,
    reset,
  };
};
