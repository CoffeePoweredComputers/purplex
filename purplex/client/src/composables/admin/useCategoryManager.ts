/**
 * useCategoryManager - Manages category selection and creation for the admin editor.
 *
 * This composable handles:
 * - Loading available categories
 * - Toggling category selection
 * - Creating new categories with color picker
 * - The "morphing bean" animation for category creation form
 */

import { ref, reactive, readonly, type Ref, type DeepReadonly, nextTick } from 'vue';
import type { ProblemCategory } from '@/types';
import { problemService } from '@/services/problemService';
import { log } from '@/utils/logger';

// ===== TYPES =====

export interface CategoryForm {
  name: string;
  color: string;
  description: string;
}

export interface PopupPosition {
  top: string;
  left: string;
}

export interface UseCategoryManagerReturn {
  /** Available categories */
  categories: Ref<ProblemCategory[]>;
  /** Selected category IDs */
  selectedIds: Ref<number[]>;
  /** Whether the create form is visible */
  showCreateForm: Ref<boolean>;
  /** Whether transitioning (for animations) */
  isTransitioning: Ref<boolean>;
  /** Whether currently creating a category */
  isCreating: Ref<boolean>;
  /** Category creation error */
  error: Ref<string | null>;
  /** New category form data */
  newCategory: DeepReadonly<CategoryForm>;
  /** Whether color picker is visible */
  showColorPicker: Ref<boolean>;
  /** Color picker popup position */
  popupPosition: DeepReadonly<PopupPosition>;
  /** Color picker direction */
  popupDirection: Ref<'above' | 'below'>;

  /** Load available categories */
  loadCategories: () => Promise<void>;
  /** Toggle a category selection */
  toggleCategory: (id: number) => void;
  /** Set selected category IDs */
  setSelectedIds: (ids: number[]) => void;

  /** Expand the create form (morphing bean animation) */
  expandForm: () => void;
  /** Collapse the create form */
  collapseForm: () => void;
  /** Create a new category */
  createCategory: () => Promise<void>;
  /** Update new category form field */
  updateNewCategory: <K extends keyof CategoryForm>(key: K, value: CategoryForm[K]) => void;
  /** Reset new category form */
  resetNewCategoryForm: () => void;

  /** Toggle color picker visibility */
  toggleColorPicker: (triggerElement: HTMLElement) => void;
  /** Close color picker */
  closeColorPicker: () => void;
  /** Select a color */
  selectColor: (color: string) => void;
  /** Calculate popup position based on trigger element */
  calculatePopupPosition: (triggerElement: HTMLElement) => void;

  /** Reset entire state */
  reset: () => void;
}

// ===== COLOR OPTIONS =====

export const COLOR_OPTIONS = [
  { value: '#3b82f6', name: 'Blue' },
  { value: '#ef4444', name: 'Red' },
  { value: '#10b981', name: 'Green' },
  { value: '#f59e0b', name: 'Orange' },
  { value: '#8b5cf6', name: 'Purple' },
  { value: '#06b6d4', name: 'Cyan' },
  { value: '#84cc16', name: 'Lime' },
  { value: '#f97316', name: 'Orange Red' },
];

// ===== COMPOSABLE =====

export const useCategoryManager = (): UseCategoryManagerReturn => {
  // Categories state
  const categories = ref<ProblemCategory[]>([]);
  const selectedIds = ref<number[]>([]);

  // Create form state
  const showCreateForm = ref(false);
  const isTransitioning = ref(false);
  const isCreating = ref(false);
  const error = ref<string | null>(null);
  const newCategory = reactive<CategoryForm>({
    name: '',
    color: '#3b82f6',
    description: '',
  });

  // Color picker state
  const showColorPicker = ref(false);
  const popupPosition = reactive<PopupPosition>({
    top: '0px',
    left: '0px',
  });
  const popupDirection = ref<'above' | 'below'>('below');

  // ===== Category Loading =====

  const loadCategories = async (): Promise<void> => {
    try {
      categories.value = await problemService.loadCategories();
    } catch (err) {
      log.error('Failed to load categories', err);
      throw err;
    }
  };

  // ===== Category Selection =====

  const toggleCategory = (id: number): void => {
    const index = selectedIds.value.indexOf(id);
    if (index === -1) {
      selectedIds.value.push(id);
    } else {
      selectedIds.value.splice(index, 1);
    }
  };

  const setSelectedIds = (ids: number[]): void => {
    selectedIds.value = ids;
  };

  // ===== Create Form (Morphing Bean) =====

  const expandForm = (): void => {
    isTransitioning.value = true;
    showCreateForm.value = true;

    // End transition after animation
    setTimeout(() => {
      isTransitioning.value = false;
    }, 300);
  };

  const collapseForm = (): void => {
    isTransitioning.value = true;

    setTimeout(() => {
      showCreateForm.value = false;
      isTransitioning.value = false;
      resetNewCategoryForm();
    }, 300);
  };

  const createCategory = async (): Promise<void> => {
    if (!newCategory.name.trim()) {
      error.value = 'Category name is required';
      return;
    }

    isCreating.value = true;
    error.value = null;

    try {
      const created = await problemService.createCategory({
        name: newCategory.name.trim(),
        color: newCategory.color,
        description: newCategory.description.trim(),
      });

      // Add to list and select it
      categories.value.push(created);
      selectedIds.value.push(created.id);

      // Collapse form
      collapseForm();
    } catch (err: unknown) {
      const errObj = err as { message?: string };
      error.value = errObj.message || 'Failed to create category';
      log.error('Failed to create category', err);
    } finally {
      isCreating.value = false;
    }
  };

  const updateNewCategory = <K extends keyof CategoryForm>(
    key: K,
    value: CategoryForm[K]
  ): void => {
    newCategory[key] = value;
  };

  const resetNewCategoryForm = (): void => {
    newCategory.name = '';
    newCategory.color = '#3b82f6';
    newCategory.description = '';
    error.value = null;
  };

  // ===== Color Picker =====

  const calculatePopupPosition = (triggerElement: HTMLElement): void => {
    const rect = triggerElement.getBoundingClientRect();
    const viewportHeight = window.innerHeight;

    // Calculate space above and below
    const spaceBelow = viewportHeight - rect.bottom;

    // Position below by default, above if not enough space
    if (spaceBelow < 200) {
      popupDirection.value = 'above';
      popupPosition.top = `${rect.top - 10}px`;
    } else {
      popupDirection.value = 'below';
      popupPosition.top = `${rect.bottom + 10}px`;
    }

    popupPosition.left = `${rect.left}px`;
  };

  const toggleColorPicker = (triggerElement: HTMLElement): void => {
    if (showColorPicker.value) {
      closeColorPicker();
    } else {
      calculatePopupPosition(triggerElement);
      showColorPicker.value = true;
    }
  };

  const closeColorPicker = (): void => {
    showColorPicker.value = false;
  };

  const selectColor = (color: string): void => {
    newCategory.color = color;
    closeColorPicker();
  };

  // ===== Reset =====

  const reset = (): void => {
    categories.value = [];
    selectedIds.value = [];
    showCreateForm.value = false;
    isTransitioning.value = false;
    isCreating.value = false;
    error.value = null;
    resetNewCategoryForm();
    closeColorPicker();
  };

  return {
    categories,
    selectedIds,
    showCreateForm,
    isTransitioning,
    isCreating,
    error,
    newCategory: readonly(newCategory),
    showColorPicker,
    popupPosition: readonly(popupPosition),
    popupDirection,
    loadCategories,
    toggleCategory,
    setSelectedIds,
    expandForm,
    collapseForm,
    createCategory,
    updateNewCategory,
    resetNewCategoryForm,
    toggleColorPicker,
    closeColorPicker,
    selectColor,
    calculatePopupPosition,
    reset,
  };
};
