/**
 * Minimal API client for the embed bundle.
 *
 * Deliberately separate from contentService.ts (admin/instructor scoped) and
 * does not import firebaseConfig/sseService/store — the embed bundle must
 * stay Firebase-free until the LTI-based embed auth (B2, #139) lands.
 */
import axios from 'axios';
import type { ActivityProblem } from '@/components/activities/types';
import { sseService } from './sseService';
import { log } from '../utils/logger';

export async function getEmbedProblem(slug: string): Promise<ActivityProblem> {
  const response = await axios.get<ActivityProblem>(`/api/problems/${slug}/`);
  return response.data;
}

/**
 * Mint the short-lived token appended to the SSE stream URL.
 *
 * Unlike the main SPA's path this never touches Firebase: it rides the shared
 * axios instance, whose interceptor already carries the embed's launch
 * credential. Once B5 (#142) lands an embed-specific endpoint, only the URL
 * below changes — the token's shape on the wire (?sse_token=) is fixed by the
 * server and stays the same.
 */
export async function getEmbedSseToken(): Promise<string | null> {
  try {
    const response = await axios.post<{ sse_token?: string }>('/api/auth/sse-token/');
    return response.data.sse_token ?? null;
  } catch (err) {
    log.error('Failed to get embed SSE session token', err);
    return null;
  }
}

/** Point sseService at the embed's token path. Called once at boot. */
export function installEmbedSseTokenProvider(): void {
  sseService.setTokenProvider(getEmbedSseToken);
}
