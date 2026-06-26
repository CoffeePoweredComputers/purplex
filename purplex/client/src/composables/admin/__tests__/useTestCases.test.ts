import { describe, expect, it } from 'vitest';
import { withSetup } from '@/test/setup';
import { parseTypeAnnotation } from '@/utils/typeSystem';
import { useTestCases } from '../useTestCases';
import type { FunctionParameter } from '../useFunctionSignature';
import type { TestCaseDisplay } from '@/types';

/**
 * Integration tests for convertForBackend type-aware conversion (#136).
 *
 * The instructor authoring panel and the persisted DB value must carry the
 * author's declared type. A str-typed function whose test case reads "123" must
 * be sent as the string "123", not coerced to int 123 — otherwise students fail
 * a correct string answer.
 */

function param(type: string): FunctionParameter {
  return {
    name: 'p',
    type,
    simplifiedType: type.toLowerCase().split('[')[0],
    typeSpec: parseTypeAnnotation(type),
  };
}

function makeCase(inputs: unknown[], expected_output: unknown): TestCaseDisplay {
  return {
    inputs,
    expected_output,
    description: '',
    is_hidden: false,
    is_sample: true,
    order: 0,
    error: null,
  } as TestCaseDisplay;
}

describe('useTestCases.convertForBackend (type-aware)', () => {
  it('keeps a numeric-looking expected_output as a string for a -> str function', () => {
    const tc = withSetup(() => useTestCases());
    tc.testCases.value = [makeCase(['456'], '123')];

    const [out] = tc.convertForBackend([param('str')], 'str');

    expect(out.expected_output).toBe('123');
    expect(typeof out.expected_output).toBe('string');
    // str-typed input argument is likewise preserved
    expect(out.inputs[0]).toBe('456');
    expect(typeof out.inputs[0]).toBe('string');
  });

  it('still coerces to int for an int-returning function', () => {
    const tc = withSetup(() => useTestCases());
    tc.testCases.value = [makeCase(['456'], '123')];

    const [out] = tc.convertForBackend([param('int')], 'int');

    expect(out.expected_output).toBe(123);
    expect(typeof out.expected_output).toBe('number');
    expect(out.inputs[0]).toBe(456);
  });

  it('falls back to auto-detection when no signature is passed (backward compatible)', () => {
    const tc = withSetup(() => useTestCases());
    tc.testCases.value = [makeCase([], '123')];

    const [out] = tc.convertForBackend();

    expect(out.expected_output).toBe(123);
  });

  it('round-trips: a stored string survives load -> save', () => {
    const tc = withSetup(() => useTestCases());
    // Simulate loading a persisted str expected_output of "123".
    const loaded = tc.convertFromBackend([makeCase([], '123')]);
    tc.testCases.value = loaded;

    const [out] = tc.convertForBackend([], 'str');

    expect(out.expected_output).toBe('123');
    expect(typeof out.expected_output).toBe('string');
  });
});
