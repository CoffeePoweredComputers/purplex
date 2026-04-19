import axios, {
  type AxiosError,
  type AxiosRequestConfig,
  type AxiosResponse,
} from 'axios';
import store from '../store';
import { log } from './logger';

interface ConsentRequiredErrorBody {
  error: string;
  code: string;
  purpose: string;
}

type ConsentAwareConfig = AxiosRequestConfig & { _consentRetried?: boolean };

/**
 * Detects `403 + code=consent_required` from the backend and coordinates with
 * the AIConsentModal to let the user grant consent and retry the original
 * request. Resolves with the retried response, or rejects with the original
 * error if the user declines or retry itself fails.
 *
 * Concurrent-call dedup lives in the consentPrompt store — we just await its
 * promise here, so N simultaneous 403s produce ONE modal.
 *
 * The `_consentRetried` flag on the request config prevents an infinite loop
 * if the retry itself somehow still returns 403 (e.g., grant silently failed,
 * policy-version bump server-side).
 */
export async function handleConsentRequired(
  error: AxiosError<ConsentRequiredErrorBody>,
): Promise<AxiosResponse> {
  const originalRequest = error.config as ConsentAwareConfig | undefined;
  if (!originalRequest || originalRequest._consentRetried) {
    return Promise.reject(error);
  }

  const purpose = error.response?.data?.purpose;
  if (!purpose) {
    log.error('Consent-required error missing purpose field', error.response?.data);
    return Promise.reject(error);
  }

  const granted: boolean = await store.dispatch(
    'consentPrompt/requestDecision',
    purpose,
  );

  if (!granted) {
    return Promise.reject(error);
  }

  originalRequest._consentRetried = true;
  return axios(originalRequest);
}

/**
 * Predicate for the response interceptor wiring. Kept exported so tests can
 * assert on detection logic without mocking the full axios stack.
 *
 * The backend's `consent_required` error code is generic — it's also returned
 * for non-AI gates like behavioral_tracking (see activity_event_views.py). We
 * match on `purpose === 'ai_processing'` so only AI-consent denials trigger
 * the modal/retry flow; other consent 403s fall through to normal error
 * handling.
 */
export function isConsentRequiredError(
  error: AxiosError<Partial<ConsentRequiredErrorBody>> | AxiosError,
): boolean {
  const data = error.response?.data as Partial<ConsentRequiredErrorBody> | undefined;
  return (
    error.response?.status === 403 &&
    data?.code === 'consent_required' &&
    data?.purpose === 'ai_processing'
  );
}
