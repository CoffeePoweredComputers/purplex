/**
 * useProblemEditor - Orchestrator composable for the admin problem editor.
 *
 * This composable wires together all feature composables and provides
 * the unified API for AdminProblemEditorShell.vue and type-specific editors.
 *
 * It handles:
 * - Coordinating state between composables
 * - High-level operations (load, save, test)
 * - Activity type configuration from /api/activity-types/
 */

import { computed, type ComputedRef, type Ref, ref, watch } from 'vue';
import axios from 'axios';
import type { ProblemDetailed, ProblemType, TestExecutionResult } from '@/types';
import { problemService } from '@/services/problemService';
import { log } from '@/utils/logger';

// Import feature composables
import { useProblemForm, type UseProblemFormReturn } from './useProblemForm';
import { useUIState, type UseUIStateReturn } from './useUIState';
import { useFunctionSignature, type UseFunctionSignatureReturn } from './useFunctionSignature';
import { useTestCases, type UseTestCasesReturn } from './useTestCases';
import { useHintsConfig, type UseHintsConfigReturn } from './useHintsConfig';
import { useMcqOptions, type UseMcqOptionsReturn } from './useMcqOptions';
import { useSegmentation, type UseSegmentationReturn } from './useSegmentation';
import { useCategoryManager, type UseCategoryManagerReturn } from './useCategoryManager';
import { usePromptConfig, type UsePromptConfigReturn } from './usePromptConfig';
import { useEditorSettings, type UseEditorSettingsReturn } from './useEditorSettings';
import { useRefuteConfig, type UseRefuteConfigReturn } from './useRefuteConfig';
import { useDebugFixConfig, type UseDebugFixConfigReturn } from './useDebugFixConfig';
import { useProbeableCodeConfig, type UseProbeableCodeConfigReturn } from './useProbeableCodeConfig';
import { useProbeableSpecConfig, type UseProbeableSpecConfigReturn } from './useProbeableSpecConfig';

// ===== TYPES =====

export interface ActivityTypeConfig {
  type: string;
  label: string;
  has_pipeline: boolean;
  admin_config?: {
    hidden_sections?: string[];
    required_fields?: string[];
    optional_fields?: string[];
    type_specific_section?: string | null;
    supports?: Record<string, boolean>;
  };
}

export interface UseProblemEditorReturn {
  // Feature composables
  form: UseProblemFormReturn;
  ui: UseUIStateReturn;
  signature: UseFunctionSignatureReturn;
  testCases: UseTestCasesReturn;
  hints: UseHintsConfigReturn;
  mcqOptions: UseMcqOptionsReturn;
  segmentation: UseSegmentationReturn;
  categories: UseCategoryManagerReturn;
  promptConfig: UsePromptConfigReturn;
  editorSettings: UseEditorSettingsReturn;
  refuteConfig: UseRefuteConfigReturn;
  debugFixConfig: UseDebugFixConfigReturn;
  probeableCodeConfig: UseProbeableCodeConfigReturn;
  probeableSpecConfig: UseProbeableSpecConfigReturn;

  // Activity type state
  availableTypes: Ref<ActivityTypeConfig[]>;
  loadingTypes: Ref<boolean>;
  typeConfig: ComputedRef<ActivityTypeConfig['admin_config'] | undefined>;

  // Editing state
  currentSlug: Ref<string | null>;
  isEditing: ComputedRef<boolean>;

  // High-level operations
  loadProblem: (slug: string) => Promise<void>;
  saveProblem: () => Promise<ProblemDetailed>;
  testProblem: () => Promise<TestExecutionResult | undefined>;
  loadActivityTypes: () => Promise<void>;

  // Utility
  shouldShowSection: (section: string) => boolean;
  extractFunctionName: () => string;
  reset: () => void;
}

// ===== COMPOSABLE =====

export const useProblemEditor = (): UseProblemEditorReturn => {
  // Initialize feature composables
  const form = useProblemForm();
  const ui = useUIState();
  const signature = useFunctionSignature();
  const testCases = useTestCases();
  const hints = useHintsConfig();
  const mcqOptions = useMcqOptions();
  const segmentation = useSegmentation();
  const categories = useCategoryManager();
  const promptConfig = usePromptConfig();
  const editorSettings = useEditorSettings();
  const refuteConfig = useRefuteConfig();
  const debugFixConfig = useDebugFixConfig();
  const probeableCodeConfig = useProbeableCodeConfig();
  const probeableSpecConfig = useProbeableSpecConfig();

  // Activity type state
  const availableTypes = ref<ActivityTypeConfig[]>([]);
  const loadingTypes = ref(false);

  // Current problem slug
  const currentSlug = ref<string | null>(null);

  // ===== Computed =====

  const isEditing = computed(() => currentSlug.value !== null);

  const typeConfig = computed(() => {
    const currentType = availableTypes.value.find(
      t => t.type === form.form.problem_type
    );
    return currentType?.admin_config;
  });

  // ===== Watch for signature changes =====

  watch(
    () => form.form.function_signature,
    (newSignature) => {
      signature.parse(newSignature);
    },
    { immediate: true }
  );

  // ===== Activity Types =====

  const loadActivityTypes = async (): Promise<void> => {
    loadingTypes.value = true;
    try {
      const response = await axios.get('/api/activity-types/');
      availableTypes.value = response.data.types || [];
    } catch (error) {
      log.error('Failed to load activity types', error);
      // Fallback to default types
      availableTypes.value = [
        { type: 'eipl', label: 'Explain in Plain Language (EiPL)', has_pipeline: true },
        { type: 'mcq', label: 'Multiple Choice Question', has_pipeline: true },
        { type: 'prompt', label: 'Prompt (Image-based EiPL)', has_pipeline: true },
      ];
    } finally {
      loadingTypes.value = false;
    }
  };

  // ===== Section Visibility =====

  const shouldShowSection = (section: string): boolean => {
    const hiddenSections = typeConfig.value?.hidden_sections || [];
    return !hiddenSections.includes(section);
  };

  // ===== Extract Function Name =====

  const extractFunctionName = (): string => {
    return signature.extractFunctionName(form.form.reference_solution);
  };

  // ===== Load Problem =====

  const loadProblem = async (slug: string): Promise<void> => {
    return ui.executeAction('load problem', async () => {
      const problemData = await problemService.loadProblem(slug);

      // Normalize and set form data (universal metadata)
      const normalized = form.normalizeFromLoad(problemData);
      form.setForm(normalized);

      // Load test cases via their composable (single source of truth)
      testCases.loadFromBackend(problemData.test_cases || []);

      // Load type-specific data
      // MCQ problems use 'options' field (polymorphic McqProblem model)
      if (problemData.options) {
        mcqOptions.setOptions(problemData.options);
      }

      if (problemData.segmentation_config) {
        segmentation.loadConfig(problemData.segmentation_config);
      }

      if (problemData.prompt_config) {
        promptConfig.loadConfig(problemData.prompt_config);
      }

      // Load hints
      await hints.load(slug);

      // Load categories
      categories.setSelectedIds(normalized.category_ids);

      // Set current slug
      currentSlug.value = slug;

      // Parse function signature
      signature.parse(normalized.function_signature);
    });
  };

  // ===== Save Problem =====

  const saveProblem = async (): Promise<ProblemDetailed> => {
    return ui.executeAction('save problem', async () => {
      // Get handler config for this problem type
      const config = typeConfig.value;
      const typeSpecificSection = config?.type_specific_section;

      // Build problem data with universal fields
      const problemData: Record<string, unknown> = {
        title: form.getApiSafeString(form.form.title),
        description: form.getApiSafeString(form.form.description),
        difficulty: form.form.difficulty,
        problem_type: form.form.problem_type,
        category_ids: categories.selectedIds.value,
        function_name: extractFunctionName() || '',
        function_signature: form.form.function_signature || '',
        reference_solution: form.getApiSafeString(form.form.reference_solution),
        tags: form.form.tags,
      };

      // Test cases - use composable's conversion (single source of truth)
      if (config?.supports?.test_cases !== false) {
        problemData.test_cases = testCases.convertForBackend();
      }

      // Segmentation (eipl, prompt types that support it)
      if (config?.supports?.segmentation) {
        problemData.segmentation_config = segmentation.formatForApi();
        problemData.requires_highlevel_comprehension = segmentation.isEnabled.value;
      }

      // MCQ options (types with type_specific_section = 'options')
      if (typeSpecificSection === 'options') {
        problemData.options = mcqOptions.getOptionsForApi();
        problemData.question_text = form.form.description;  // MCQ uses description as question_text
      }

      // Prompt config (types with type_specific_section = 'prompt_config')
      if (typeSpecificSection === 'prompt_config') {
        problemData.prompt_config = promptConfig.getConfigForApi();
      }

      // Save
      let savedProblem: ProblemDetailed;
      if (isEditing.value && currentSlug.value) {
        savedProblem = await problemService.updateProblem(currentSlug.value, problemData);
      } else {
        savedProblem = await problemService.createProblem(problemData);
        currentSlug.value = savedProblem.slug;
      }

      // Update form with saved data
      const normalized = form.normalizeFromLoad(savedProblem);
      form.setForm(normalized);

      // Reload test cases from saved data
      testCases.loadFromBackend(savedProblem.test_cases || []);

      // Save hints (only for existing problems)
      if (isEditing.value && currentSlug.value) {
        await hints.save(currentSlug.value);
      }

      return savedProblem;
    }, isEditing.value ? 'Problem updated successfully' : 'Problem created successfully');
  };

  // ===== Test Problem =====

  const testProblem = async (): Promise<TestExecutionResult | undefined> => {
    return ui.executeAction('test problem', async () => {
      const testData = {
        title: form.form.title,
        description: '',
        function_name: extractFunctionName(),
        reference_solution: form.form.reference_solution,
        test_cases: testCases.convertForBackend(),
      };

      const results = await problemService.testProblem(testData);
      ui.setTestResults(results);
      return results;
    });
  };

  // ===== Reset =====

  const reset = (): void => {
    form.resetForm();
    signature.reset();
    testCases.setTestCases([]);
    hints.reset();
    mcqOptions.reset();
    segmentation.reset();
    categories.reset();
    promptConfig.reset();
    editorSettings.reset();
    refuteConfig.reset();
    debugFixConfig.reset();
    probeableCodeConfig.reset();
    probeableSpecConfig.reset();
    currentSlug.value = null;
    ui.clearError();
    ui.clearTestResults();
  };

  return {
    // Feature composables
    form,
    ui,
    signature,
    testCases,
    hints,
    mcqOptions,
    segmentation,
    categories,
    promptConfig,
    editorSettings,
    refuteConfig,
    debugFixConfig,
    probeableCodeConfig,
    probeableSpecConfig,

    // Activity type state
    availableTypes,
    loadingTypes,
    typeConfig,

    // Editing state
    currentSlug,
    isEditing,

    // High-level operations
    loadProblem,
    saveProblem,
    testProblem,
    loadActivityTypes,

    // Utility
    shouldShowSection,
    extractFunctionName,
    reset,
  };
};
