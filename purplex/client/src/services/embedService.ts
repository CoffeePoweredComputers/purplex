/**
 * Minimal API client for the embed bundle.
 *
 * Deliberately separate from contentService.ts (admin/instructor scoped) and
 * does not import firebaseConfig/sseService/store — the embed bundle must
 * stay Firebase-free until the LTI-based embed auth (B2, #139) lands.
 */
import axios from 'axios';
import type { ActivityProblem } from '@/components/activities/types';

export async function getEmbedProblem(slug: string): Promise<ActivityProblem> {
  const response = await axios.get<ActivityProblem>(`/api/problems/${slug}/`);
  return response.data;
}
