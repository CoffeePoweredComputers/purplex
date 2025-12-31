/**
 * Utility functions for properly formatting test values in the UI,
 * especially for handling falsy values that are legitimate outputs.
 */

/**
 * Check if a value is truly missing (null or undefined)
 * as opposed to being a legitimate falsy value like false, 0, "", [], {}
 */
export function isMissingValue(value: unknown): boolean {
  return value === null || value === undefined;
}

/**
 * Format a test value as a Python literal for display
 * Shows values exactly as they would appear in Python code
 */
export function formatTestValueAsPython(value: unknown): string {
  // Handle truly missing values
  if (value === null || value === undefined) {
    return 'None';
  }

  // Handle boolean values - Python uses True/False (capitalized)
  if (value === false) {return 'False';}
  if (value === true) {return 'True';}

  // Handle strings - Python typically uses single quotes
  if (typeof value === 'string') {
    // Empty string
    if (value === '') {return "''";}

    // Check if string contains single quotes
    if (value.includes("'") && !value.includes('"')) {
      // Use double quotes if string contains single quotes
      return `"${value}"`;
    } else if (value.includes("'")) {
      // Escape single quotes if string contains both types
      return `'${value.replace(/'/g, "\\'")}'`;
    } else {
      // Default to single quotes (Python convention)
      return `'${value}'`;
    }
  }

  // Handle numbers (including 0)
  if (typeof value === 'number') {
    return String(value);
  }

  // Handle arrays/lists
  if (Array.isArray(value)) {
    if (value.length === 0) {return '[]';}

    // Recursively format array elements as Python
    const elements = value.map(item => formatTestValueAsPython(item));
    return `[${elements.join(', ')}]`;
  }

  // Handle objects/dicts
  if (typeof value === 'object' && value !== null) {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj);
    if (keys.length === 0) {return '{}';}

    // Format as Python dict with single-quoted keys
    const pairs = keys.map(key => {
      const formattedKey = formatTestValueAsPython(key);
      const formattedValue = formatTestValueAsPython(obj[key]);
      return `${formattedKey}: ${formattedValue}`;
    });
    return `{${pairs.join(', ')}}`;
  }

  // Default fallback
  return String(value);
}

/**
 * Format a test value for display, preserving falsy values
 * and making them visually clear to students
 * Now uses Python formatting for consistency with Python problems
 */
export function formatTestValue(value: unknown): string {
  return formatTestValueAsPython(value);
}

/**
 * Get a semantic label for the value type to help students understand
 * what their function returned
 */
export function getValueTypeLabel(value: unknown): string {
  if (isMissingValue(value)) {return 'none';}
  if (value === false || value === true) {return 'boolean';}
  if (value === '') {return 'empty-string';}
  if (Array.isArray(value) && value.length === 0) {return 'empty-array';}
  if (typeof value === 'object' && Object.keys(value).length === 0) {return 'empty-object';}
  if (typeof value === 'number' && value === 0) {return 'zero';}
  if (typeof value === 'number') {return 'number';}
  if (typeof value === 'string') {return 'string';}
  if (Array.isArray(value)) {return 'array';}
  if (typeof value === 'object') {return 'object';}
  return 'unknown';
}

/**
 * Get a CSS class for styling based on value type
 */
export function getValueDisplayClass(value: unknown): string {
  const type = getValueTypeLabel(value);
  return `test-value-${type}`;
}
