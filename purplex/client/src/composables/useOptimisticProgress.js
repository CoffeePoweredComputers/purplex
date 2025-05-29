import { ref } from 'vue';

export const useOptimisticProgress = () => {
  const optimisticUpdates = ref(new Map());
  
  const updateProgress = (problemSlug, update) => {
    // Store optimistic update
    optimisticUpdates.value.set(problemSlug, {
      ...update,
      isOptimistic: true,
      timestamp: Date.now()
    });
    
    // Return a rollback function
    return () => {
      optimisticUpdates.value.delete(problemSlug);
    };
  };
  
  const getProgress = (problemSlug, actualProgress) => {
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
  
  const clearOptimistic = (problemSlug) => {
    optimisticUpdates.value.delete(problemSlug);
  };
  
  const clearAllOptimistic = () => {
    optimisticUpdates.value.clear();
  };
  
  return {
    updateProgress,
    getProgress,
    clearOptimistic,
    clearAllOptimistic
  };
};