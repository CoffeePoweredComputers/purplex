import { ref, type Ref } from 'vue';
import type { ProgressUpdate, OptimisticProgressUpdate } from '../types';

export interface ProgressData extends ProgressUpdate {
  // Allow additional properties that might come from the server
  [key: string]: unknown;
}

export type RollbackFunction = () => void;

export interface UseOptimisticProgressReturn {
  updateProgress: (problemSlug: string, update: ProgressUpdate) => RollbackFunction;
  getProgress: (problemSlug: string, actualProgress: ProgressData) => ProgressData;
  clearOptimistic: (problemSlug: string) => void;
  clearAllOptimistic: () => void;
}

export const useOptimisticProgress = (): UseOptimisticProgressReturn => {
  const optimisticUpdates: Ref<Map<string, OptimisticProgressUpdate>> = ref(new Map());
  
  const updateProgress = (problemSlug: string, update: ProgressUpdate): RollbackFunction => {
    // Store optimistic update
    optimisticUpdates.value.set(problemSlug, {
      ...update,
      isOptimistic: true,
      timestamp: Date.now()
    });
    
    // Return a rollback function
    return (): void => {
      optimisticUpdates.value.delete(problemSlug);
    };
  };
  
  const getProgress = (problemSlug: string, actualProgress: ProgressData): ProgressData => {
    const optimistic = optimisticUpdates.value.get(problemSlug);
    
    // If we have an optimistic update, merge it with actual
    if (optimistic) {
      return {
        ...actualProgress,
        ...optimistic,
        isOptimistic: true
      };
    }
    
    return actualProgress;
  };
  
  const clearOptimistic = (problemSlug: string): void => {
    optimisticUpdates.value.delete(problemSlug);
  };
  
  const clearAllOptimistic = (): void => {
    optimisticUpdates.value.clear();
  };
  
  return {
    updateProgress,
    getProgress,
    clearOptimistic,
    clearAllOptimistic
  };
};