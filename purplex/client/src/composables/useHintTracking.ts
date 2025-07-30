import { computed, ComputedRef, Ref, ref } from 'vue'
import { log } from '../utils/logger'

// Types
interface HintUsage {
  type: string
  timestamp: string
  attemptNumber: number
}

interface ProblemHintData {
  problemSlug: string
  courseId?: string | null
  problemSetSlug?: string | null
  hintsUsed: HintUsage[]
  firstHintTime: string | null
  lastHintTime: string | null
}

interface HintStatistics {
  totalProblemsWithHints: number
  totalHintsUsed: number
  hintTypeDistribution: {
    structural: number
    implementation: number
    edge_case: number
    [key: string]: number
  }
  averageHintsPerProblem: number
  problems: Array<{
    key: string
    problemSlug: string
    courseId?: string | null
    problemSetSlug?: string | null
    hintsUsed: number
    hintTypes: string[]
    timeToFirstHint: string | null
    lastHintTime: string | null
  }>
}

interface TrackingMetadata {
  courseId?: string | null
  problemSetSlug?: string | null
  attemptNumber?: number
}

// Store hint usage data per session
const hintUsageData = ref<Map<string, ProblemHintData>>(new Map())

export function useHintTracking() {
  /**
   * Track hint usage for a specific problem
   * @param {string} problemSlug - The problem identifier
   * @param {string} hintType - The type of hint used
   * @param {Object} metadata - Additional metadata (courseId, problemSetSlug, timestamp)
   */
  const trackHintUsage = (problemSlug: string, hintType: string, metadata: TrackingMetadata = {}): void => {
    const key = `${problemSlug}_${metadata.courseId || 'standalone'}_${metadata.problemSetSlug || 'default'}`
    
    if (!hintUsageData.value.has(key)) {
      hintUsageData.value.set(key, {
        problemSlug,
        courseId: metadata.courseId || null,
        problemSetSlug: metadata.problemSetSlug || null,
        hintsUsed: [],
        firstHintTime: null,
        lastHintTime: null
      })
    }
    
    const problemData = hintUsageData.value.get(key)!
    const timestamp = new Date().toISOString()
    
    // Add hint usage if not already tracked
    if (!problemData.hintsUsed.find(h => h.type === hintType)) {
      problemData.hintsUsed.push({
        type: hintType,
        timestamp,
        attemptNumber: metadata.attemptNumber || 0
      })
      
      if (!problemData.firstHintTime) {
        problemData.firstHintTime = timestamp
      }
      problemData.lastHintTime = timestamp
    }
    
    // Persist to localStorage for research data
    persistHintData()
  }
  
  /**
   * Get hint usage for a specific problem
   * @param {string} problemSlug - The problem identifier
   * @param {string} courseId - Optional course ID
   * @param {string} problemSetSlug - Optional problem set slug
   * @returns {Array} Array of hint types used
   */
  const getHintsUsed = (problemSlug: string, courseId: string | null = null, problemSetSlug: string | null = null): string[] => {
    const key = `${problemSlug}_${courseId || 'standalone'}_${problemSetSlug || 'default'}`
    const problemData = hintUsageData.value.get(key)
    return problemData?.hintsUsed.map(h => h.type) || []
  }
  
  /**
   * Check if a specific hint has been used
   * @param {string} problemSlug - The problem identifier
   * @param {string} hintType - The hint type to check
   * @param {string} courseId - Optional course ID
   * @param {string} problemSetSlug - Optional problem set slug
   * @returns {boolean} Whether the hint has been used
   */
  const isHintUsed = (problemSlug: string, hintType: string, courseId: string | null = null, problemSetSlug: string | null = null): boolean => {
    const hintsUsed = getHintsUsed(problemSlug, courseId, problemSetSlug)
    return hintsUsed.includes(hintType)
  }
  
  /**
   * Get hint usage statistics for research
   * @returns {Object} Aggregated hint usage statistics
   */
  const getHintStatistics = (): HintStatistics => {
    const stats: HintStatistics = {
      totalProblemsWithHints: hintUsageData.value.size,
      totalHintsUsed: 0,
      hintTypeDistribution: {
        structural: 0,
        implementation: 0,
        edge_case: 0
      },
      averageHintsPerProblem: 0,
      problems: []
    }
    
    hintUsageData.value.forEach((data, key) => {
      stats.totalHintsUsed += data.hintsUsed.length
      
      data.hintsUsed.forEach(hint => {
        if (stats.hintTypeDistribution[hint.type] !== undefined) {
          stats.hintTypeDistribution[hint.type]++
        }
      })
      
      stats.problems.push({
        key,
        problemSlug: data.problemSlug,
        courseId: data.courseId,
        problemSetSlug: data.problemSetSlug,
        hintsUsed: data.hintsUsed.length,
        hintTypes: data.hintsUsed.map(h => h.type),
        timeToFirstHint: data.firstHintTime,
        lastHintTime: data.lastHintTime
      })
    })
    
    if (stats.totalProblemsWithHints > 0) {
      stats.averageHintsPerProblem = stats.totalHintsUsed / stats.totalProblemsWithHints
    }
    
    return stats
  }
  
  /**
   * Clear hint usage data (for testing or reset)
   */
  const clearHintData = (): void => {
    hintUsageData.value.clear()
    localStorage.removeItem('purplex_hint_usage_data')
  }
  
  /**
   * Persist hint data to localStorage
   */
  const persistHintData = (): void => {
    const dataArray = Array.from(hintUsageData.value.entries())
    localStorage.setItem('purplex_hint_usage_data', JSON.stringify(dataArray))
  }
  
  /**
   * Load hint data from localStorage
   */
  const loadHintData = (): void => {
    try {
      const stored = localStorage.getItem('purplex_hint_usage_data')
      if (stored) {
        const dataArray = JSON.parse(stored)
        hintUsageData.value = new Map(dataArray)
      }
    } catch (error) {
      log.error('Error loading hint data', error)
    }
  }
  
  // Load data on initialization
  loadHintData()
  
  return {
    trackHintUsage,
    getHintsUsed,
    isHintUsed,
    getHintStatistics,
    clearHintData,
    hintUsageData: computed(() => hintUsageData.value) as ComputedRef<Map<string, ProblemHintData>>
  }
}