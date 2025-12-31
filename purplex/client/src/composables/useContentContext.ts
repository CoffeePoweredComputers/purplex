/**
 * useContentContext - Role-aware context for content management components.
 *
 * This composable provides a consistent way for content management components
 * (problem editor, problem sets, etc.) to access role-specific configuration
 * without needing to know which role they're running under.
 *
 * Architecture:
 * - provideContentContext() is called by layout/wrapper components
 * - useContentContext() is called by child components that need role-aware behavior
 *
 * The role is determined by:
 * 1. Route path prefix (/admin vs /instructor)
 * 2. Fallback to user's actual role from auth store
 *
 * Usage:
 *   // In layout component:
 *   const ctx = provideContentContext()
 *
 *   // In child component:
 *   const ctx = useContentContext()
 *   await ctx.api.getProblem(slug)
 */
import {
  computed,
  inject,
  provide,
  type ComputedRef,
  type InjectionKey
} from 'vue';
import { useRoute, useRouter } from 'vue-router';
import store from '@/store';
import {
  adminContentService,
  instructorContentService,
  type ContentApiService,
  type ContentRole
} from '@/services/contentService';

/**
 * Content context interface - what's available to all content components.
 */
export interface ContentContext {
  /** Current role: 'admin' or 'instructor' */
  role: ComputedRef<ContentRole>;

  /** Base path for navigation (e.g., '/admin' or '/instructor') */
  basePath: ComputedRef<string>;

  /** API service configured for current role */
  api: ComputedRef<ContentApiService>;

  /** Navigation helpers */
  paths: {
    // Problems
    problems: ComputedRef<string>;
    newProblem: ComputedRef<string>;
    editProblem: (slug: string) => string;
    // Problem Sets
    problemSets: ComputedRef<string>;
    newProblemSet: ComputedRef<string>;
    editProblemSet: (slug: string) => string;
    // Courses
    courses: ComputedRef<string>;
    newCourse: ComputedRef<string>;
    editCourse: (courseId: string) => string;
    courseStudents: (courseId: string) => string;
    courseProblemSets: (courseId: string) => string;
    // Submissions
    submissions: ComputedRef<string>;
    courseSubmissions: (courseId: string) => string;
  };

  /** Role checks */
  isAdmin: ComputedRef<boolean>;
  isInstructor: ComputedRef<boolean>;

  /** Navigation function for after save/delete */
  navigateToList: (listType: 'problems' | 'problem-sets') => void;

  /** Page titles based on role */
  getPageTitle: (base: string) => ComputedRef<string>;
}

const ContentContextKey: InjectionKey<ContentContext> = Symbol('ContentContext');

/**
 * Provide content context to child components.
 * Call this in your layout/wrapper component.
 *
 * @returns ContentContext that's also provided to descendants
 */
export function provideContentContext(): ContentContext {
  const route = useRoute();
  const router = useRouter();

  // Determine role from route prefix, fallback to user role
  const role = computed<ContentRole>(() => {
    const path = route.path;
    if (path.startsWith('/admin')) return 'admin';
    if (path.startsWith('/instructor')) return 'instructor';

    // Fallback to user's actual role
    const isAdminUser = store.getters['auth/isAdmin'];
    return isAdminUser ? 'admin' : 'instructor';
  });

  // Base path for building URLs
  const basePath = computed(() => `/${role.value}`);

  // Select appropriate API service
  const api = computed(() =>
    role.value === 'admin' ? adminContentService : instructorContentService
  );

  // Role checks
  const isAdmin = computed(() => role.value === 'admin');
  const isInstructor = computed(() => role.value === 'instructor');

  // Navigation paths
  const paths = {
    // Problems
    problems: computed(() => `${basePath.value}/problems`),
    newProblem: computed(() => `${basePath.value}/problems/new`),
    editProblem: (slug: string) => `${basePath.value}/problems/${slug}/edit`,
    // Problem Sets
    problemSets: computed(() => `${basePath.value}/problem-sets`),
    newProblemSet: computed(() => `${basePath.value}/problem-sets/new`),
    editProblemSet: (slug: string) => `${basePath.value}/problem-sets/${slug}/edit`,
    // Courses
    courses: computed(() => `${basePath.value}/courses`),
    newCourse: computed(() => `${basePath.value}/courses/new`),
    editCourse: (courseId: string) => `${basePath.value}/courses/${courseId}/edit`,
    courseStudents: (courseId: string) => `${basePath.value}/courses/${courseId}/students`,
    courseProblemSets: (courseId: string) => `${basePath.value}/courses/${courseId}/problem-sets`,
    // Submissions
    submissions: computed(() => `${basePath.value}/submissions`),
    courseSubmissions: (courseId: string) => `${basePath.value}/courses/${courseId}/submissions`,
  };

  // Navigation helper
  const navigateToList = (listType: 'problems' | 'problem-sets' | 'courses') => {
    let path: string;
    switch (listType) {
      case 'problems':
        path = paths.problems.value;
        break;
      case 'problem-sets':
        path = paths.problemSets.value;
        break;
      case 'courses':
        path = paths.courses.value;
        break;
    }
    router.push(path);
  };

  // Title helper - adds role context to base title
  const getPageTitle = (base: string) => computed(() => {
    if (role.value === 'instructor') {
      // Instructor sees "My X" instead of "X"
      if (base === 'Problems') return 'My Problems';
      if (base === 'Problem Sets') return 'My Problem Sets';
      if (base === 'Courses') return 'My Courses';
    }
    return base;
  });

  const context: ContentContext = {
    role,
    basePath,
    api,
    paths,
    isAdmin,
    isInstructor,
    navigateToList,
    getPageTitle,
  };

  // Provide to descendants
  provide(ContentContextKey, context);

  return context;
}

/**
 * Use content context from a parent provider.
 * Must be called within a component that has ContentEditorLayout as an ancestor.
 *
 * @throws Error if called outside of content context
 */
export function useContentContext(): ContentContext {
  const context = inject(ContentContextKey);
  if (!context) {
    throw new Error(
      'useContentContext must be used within a component wrapped by ContentEditorLayout ' +
      'or another component that calls provideContentContext()'
    );
  }
  return context;
}

/**
 * Try to use content context, returning undefined if not available.
 * Useful for components that can work with or without context.
 */
export function useContentContextOptional(): ContentContext | undefined {
  return inject(ContentContextKey);
}

export type { ContentRole, ContentApiService };
