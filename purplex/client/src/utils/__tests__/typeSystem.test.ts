import { describe, expect, it } from 'vitest';
import { convertWithDeclaredType } from '../typeSystem';

/**
 * Tests for convertWithDeclaredType — the type-aware conversion that closes the
 * #136 class of bug: a str-typed field whose text looks numeric must NOT be
 * coerced to a number.
 */
describe('convertWithDeclaredType', () => {
  describe('str-typed fields are taken as string literals', () => {
    it('keeps an unquoted numeric string as a string', () => {
      const result = convertWithDeclaredType('123', 'str');
      expect(result).toBe('123');
      expect(typeof result).toBe('string');
    });

    it('preserves leading zeros (007 stays "007", not 7)', () => {
      expect(convertWithDeclaredType('007', 'str')).toBe('007');
    });

    it('strips optional surrounding quotes', () => {
      expect(convertWithDeclaredType('"123"', 'str')).toBe('123');
      expect(convertWithDeclaredType("'hello'", 'str')).toBe('hello');
    });

    it('keeps a json-looking string as a string', () => {
      expect(convertWithDeclaredType('true', 'str')).toBe('true');
      expect(convertWithDeclaredType('[1, 2]', 'str')).toBe('[1, 2]');
    });
  });

  describe('non-str declared types keep auto-detection', () => {
    it('converts a numeric string to int for an int field', () => {
      const result = convertWithDeclaredType('123', 'int');
      expect(result).toBe(123);
      expect(typeof result).toBe('number');
    });

    it('converts to float for a float field', () => {
      expect(convertWithDeclaredType('3.14', 'float')).toBe(3.14);
    });

    it('converts to bool for a bool field', () => {
      expect(convertWithDeclaredType('true', 'bool')).toBe(true);
    });

    it('converts to a list for a list field', () => {
      expect(convertWithDeclaredType('[1, 2]', 'list')).toEqual([1, 2]);
    });
  });

  describe('Any / unknown falls back to auto-detection (backward compatible)', () => {
    it('auto-detects a numeric string as int when type is Any', () => {
      expect(convertWithDeclaredType('123', 'Any')).toBe(123);
    });

    it('auto-detects when type is empty', () => {
      expect(convertWithDeclaredType('123', '')).toBe(123);
    });
  });
});
