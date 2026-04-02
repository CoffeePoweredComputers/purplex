import { ActionContext, Module } from 'vuex';
import axios from 'axios';
import { AuthState } from './auth.module';
import { log } from '../utils/logger';

// ===== TYPE DEFINITIONS =====

export interface Course {
  course_id: string;
  name: string;
  description: string;
  instructor_name?: string;
  problem_sets?: CourseProblemSet[];
  created_at?: string;
  updated_at?: string;
  is_enrolled?: boolean;
}

export interface CourseProblemSet {
  id: number;
  name: string;
  description: string;
  slug: string;
  problems_count?: number;
  icon?: string;
  order?: number;
  is_required?: boolean;
  due_date?: string | null;
}

export interface CourseEnrollment {
  course: Course;
  enrolled_at: string;
  progress: CourseProgress;
}

export interface CourseProgress {
  completed_sets: number;
  total_sets: number;
  percentage: number;
  last_activity: string | null;
}

export interface EnrollmentModal {
  visible: boolean;
  loading: boolean;
  coursePreview: Course | null;
  error: string | null;
}

export interface LoadingStates {
  courses: boolean;
  enrollment: boolean;
}

export interface StudentProgress {
  [studentId: string]: {
    student_name: string;
    progress: CourseProgress;
    problem_sets: {
      [problemSetId: string]: {
        completed: boolean;
        score: number;
        last_activity: string;
      };
    };
  };
}

export interface CoursesState {
  // Core course data
  enrolledCourses: CourseEnrollment[];
  availableProblemSets: CourseProblemSet[];
  currentCourse: Course | null;

  // UI state
  enrollmentModal: EnrollmentModal;

  // Instructor-specific state
  instructorCourses: Course[];
  studentProgress: Record<string, StudentProgress>;

  // Loading states
  loading: LoadingStates;
}

export interface OrganizedCourses {
  active: CourseEnrollment[];
  completed: CourseEnrollment[];
}

// API Response types
export interface CourseEnrollmentResponse {
  message: string;
  enrollment: CourseEnrollment;
}

export interface CourseLookupResponse {
  course: Course;
  already_enrolled: boolean;
}


// ===== VUEX MODULE TYPES =====

interface RootState {
  auth: AuthState;
  courses: CoursesState;
}

type CoursesActionContext = ActionContext<CoursesState, RootState>;

// ===== INITIAL STATE =====

const initialState: CoursesState = {
  // Core course data
  enrolledCourses: [],        // Array of courses user is enrolled in
  availableProblemSets: [],   // Problem sets for browsing when adding to course
  currentCourse: null,        // Active course being viewed

  // UI state
  enrollmentModal: {
    visible: false,
    loading: false,
    coursePreview: null,
    error: null
  },

  // Instructor-specific state
  instructorCourses: [],      // Courses where user is instructor
  studentProgress: {},        // Student progress data for instructor view

  // Loading states
  loading: {
    courses: false,
    enrollment: false
  }
};

// ===== MODULE DEFINITION =====

export const courses: Module<CoursesState, RootState> = {
  namespaced: true,

  state: initialState,

  getters: {
    // Check enrollment status
    isEnrolledInCourse: (state: CoursesState) => (courseId: string): boolean => {
      return state.enrolledCourses.some(c => c.course.course_id === courseId);
    },

    // Get problem sets for current course
    getCurrentCourseProblemSets: (state: CoursesState): CourseProblemSet[] => {
      if (!state.currentCourse) {return [];}
      return state.currentCourse.problem_sets || [];
    },

    // Check if user is instructor of any course
    isInstructor: (_state: CoursesState, _getters: unknown, rootState: RootState): boolean => {
      return rootState.auth.user?.role === 'instructor' ||
             rootState.auth.user?.role === 'admin';
    },

    // Get organized courses by completion status
    organizedCourses: (state: CoursesState): OrganizedCourses => {
      return {
        active: state.enrolledCourses.filter(c => {
          return c.progress.percentage < 100;
        }),
        completed: state.enrolledCourses.filter(c => {
          return c.progress.percentage === 100;
        })
      };
    }
  },

  mutations: {
    // Course data mutations
    SET_ENROLLED_COURSES(state: CoursesState, courses: CourseEnrollment[]): void {
      state.enrolledCourses = courses;
    },

    ADD_ENROLLED_COURSE(state: CoursesState, courseData: CourseEnrollment): void {
      state.enrolledCourses.push(courseData);
    },

    SET_CURRENT_COURSE(state: CoursesState, course: Course | null): void {
      state.currentCourse = course;
    },

    // Enrollment modal mutations
    SET_ENROLLMENT_MODAL(state: CoursesState, data: Partial<EnrollmentModal>): void {
      state.enrollmentModal = { ...state.enrollmentModal, ...data };
    },

    RESET_ENROLLMENT_MODAL(state: CoursesState): void {
      state.enrollmentModal = {
        visible: false,
        loading: false,
        coursePreview: null,
        error: null
      };
    },

    // Instructor mutations
    SET_INSTRUCTOR_COURSES(state: CoursesState, courses: Course[]): void {
      state.instructorCourses = courses;
    },

    SET_STUDENT_PROGRESS(state: CoursesState, { courseId, progress }: { courseId: string; progress: StudentProgress }): void {
      state.studentProgress = {
        ...state.studentProgress,
        [courseId]: progress
      };
    },

    // Loading state mutations
    SET_LOADING(state: CoursesState, { key, value }: { key: keyof LoadingStates; value: boolean }): void {
      state.loading[key] = value;
    }
  },

  actions: {
    // Initialize course data on app load
    async initializeCourses({ dispatch, rootGetters }: CoursesActionContext): Promise<void> {
      if (rootGetters['auth/isLoggedIn']) {
        await dispatch('fetchEnrolledCourses');

        if (rootGetters['auth/isInstructor']) {
          await dispatch('fetchInstructorCourses');
        }
      }
    },

    // Fetch user's enrolled courses
    async fetchEnrolledCourses({ commit }: CoursesActionContext): Promise<CourseEnrollment[]> {
      commit('SET_LOADING', { key: 'courses', value: true });
      try {
        const response = await axios.get<CourseEnrollment[]>('/api/courses/enrolled/');
        commit('SET_ENROLLED_COURSES', response.data);
        return response.data;
      } catch (error) {
        log.error('Failed to fetch enrolled courses', error);
        throw error;
      } finally {
        commit('SET_LOADING', { key: 'courses', value: false });
      }
    },

    // Course enrollment flow
    async lookupCourse({ commit }: CoursesActionContext, courseId: string): Promise<CourseLookupResponse> {
      commit('SET_ENROLLMENT_MODAL', { loading: true, error: null });

      try {
        const response = await axios.post<CourseLookupResponse>('/api/courses/lookup/', {
          course_id: courseId
        });
        commit('SET_ENROLLMENT_MODAL', {
          coursePreview: { ...response.data.course, is_enrolled: response.data.already_enrolled },
          loading: false
        });
        return response.data;
      } catch (error: unknown) {
        const axiosError = error as { response?: { data?: { error?: string } } };
        const errorMsg = axiosError.response?.data?.error || 'Course not found';
        commit('SET_ENROLLMENT_MODAL', {
          error: errorMsg,
          loading: false,
          coursePreview: null
        });
        throw error;
      }
    },

    async enrollInCourse({ commit, dispatch }: CoursesActionContext, courseId: string): Promise<CourseEnrollmentResponse> {
      commit('SET_ENROLLMENT_MODAL', { loading: true });

      try {
        const response = await axios.post<CourseEnrollmentResponse>('/api/courses/enroll/', {
          course_id: courseId
        });

        // Refresh enrolled courses (which now includes progress)
        await dispatch('fetchEnrolledCourses');

        // Reset modal
        commit('RESET_ENROLLMENT_MODAL');

        return response.data;
      } catch (error: unknown) {
        const axiosError = error as { response?: { data?: { error?: string } } };
        const errorMsg = axiosError.response?.data?.error || 'Enrollment failed';
        commit('SET_ENROLLMENT_MODAL', { error: errorMsg, loading: false });
        throw error;
      }
    },

    // Navigate to course context
    async enterCourseContext({ commit }: CoursesActionContext, courseId: string): Promise<Course> {
      try {
        const response = await axios.get<Course>(`/api/courses/${courseId}/`);
        commit('SET_CURRENT_COURSE', response.data);
        return response.data;
      } catch (error) {
        log.error('Failed to load course', error);
        throw error;
      }
    },

    // Leave course context (back to home)
    leaveCourseContext({ commit }: CoursesActionContext): void {
      commit('SET_CURRENT_COURSE', null);
    },

    // Instructor actions
    async fetchInstructorCourses({ commit }: CoursesActionContext): Promise<Course[]> {
      try {
        const response = await axios.get<Course[]>('/api/instructor/courses/');
        commit('SET_INSTRUCTOR_COURSES', response.data);
        return response.data;
      } catch (error) {
        log.error('Failed to fetch instructor courses', error);
        throw error;
      }
    },

    async fetchStudentProgress({ commit }: CoursesActionContext, courseId: string): Promise<StudentProgress> {
      try {
        const response = await axios.get<StudentProgress>(
          `/api/instructor/courses/${courseId}/progress/`
        );
        commit('SET_STUDENT_PROGRESS', { courseId, progress: response.data });
        return response.data;
      } catch (error) {
        log.error('Failed to fetch student progress', error);
        throw error;
      }
    },

    // Show/hide enrollment modal
    showEnrollmentModal({ commit }: CoursesActionContext): void {
      commit('SET_ENROLLMENT_MODAL', { visible: true });
    },

    hideEnrollmentModal({ commit }: CoursesActionContext): void {
      commit('RESET_ENROLLMENT_MODAL');
    }
  }
};
