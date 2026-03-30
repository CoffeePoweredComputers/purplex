/**
 * Shared API error resolution.
 *
 * Resolves backend error codes to translated i18n strings, with
 * fallback to the raw error message, then a generic i18n key.
 *
 * Usage in components:
 *   import { resolveApiError } from '@/utils/errorResolver'
 *
 *   catch (err) {
 *     errorMsg.value = resolveApiError(err, 'common.errors.generic', t)
 *   }
 */

type TranslateFn = (key: string) => string;

/**
 * Resolve an API error to a user-facing translated string.
 *
 * Checks (in order):
 * 1. Backend error `code` → i18n key `errors.api.{code}`
 * 2. Backend `error` string (English fallback from server)
 * 3. Generic i18n fallback key
 *
 * Works with both APIError objects (from contentService/problemService)
 * and any error shape that has `error` and/or `code` properties.
 */
export function resolveApiError(
  err: unknown,
  fallbackKey: string,
  t: TranslateFn,
): string {
  const apiErr = err as { error?: string; code?: string };

  // Try i18n key from error code
  if (apiErr?.code) {
    const i18nKey = `errors.api.${apiErr.code}`;
    const translated = t(i18nKey);
    if (translated !== i18nKey) {
      return translated;
    }
  }

  // Fall back to error string from backend, then generic i18n key
  return apiErr?.error || t(fallbackKey);
}
