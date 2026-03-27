/**
 * Unified Content Service
 *
 * Factory pattern service that provides role-agnostic content management APIs.
 * The same interface works for both admin and instructor roles, with the
 * backend handling scope/permissions based on the endpoint prefix.
 *
 * Usage:
 *   const api = createContentService('admin')    // Global access
 *   const api = createContentService('instructor') // Ownership-scoped
 */
import axios, { AxiosResponse } from 'axios';
import type {
  APIError,
  Course,
  CourseInstructorMember,
  CourseInstructorRole,
  CourseProblemSet,
  CourseStudent,
  HintConfig,
  Instructor,
  ProblemCategory,
  ProblemDetailed,
  ProblemSet,
  SubmissionDetailed,
  TestExecutionResult
} from '@/types';

// ============ SUBMISSION TYPES ============

/**
 * Query parameters for fetching submissions.
 */
export interface SubmissionQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  problem_set?: string;
  course?: string;       // admin only: optional course filter
  course_id?: string;    // instructor only: required course scope (from route)
}

/**
 * Filter metadata returned with submission list.
 */
export interface SubmissionFilters {
  problem_sets: Array<{ slug: string; title: string }>;
  courses?: Array<{ id: string; name: string }>;  // admin only
  statuses: string[];
}

/**
 * Summary submission for list views (lighter than SubmissionDetailed).
 */
export interface SubmissionSummary {
  id: number;
  user: string;
  user_id?: number;
  problem: string;
  problem_slug: string;
  problem_set: string | null;
  problem_set_slug?: string | null;
  course?: string;
  course_id?: string;
  submission_type: string;
  score: number;
  status: string;
  comprehension_level: string | null;
  is_correct: boolean;
  execution_status: string;
  submitted_at: string;
  passed_all_tests: boolean;
  execution_time_ms: number | null;
}

/**
 * Paginated response for submission list.
 */
export interface PaginatedSubmissions {
  results: SubmissionSummary[];
  count: number;
  total_pages: number;
  current_page: number;
  next: string | null;
  previous: string | null;
  filters: SubmissionFilters;
}

export type ContentRole = 'admin' | 'instructor';

/**
 * Interface for content management operations.
 * Both admin and instructor services implement this interface.
 */
export interface ContentApiService {
  // Problems
  getProblems(): Promise<ProblemDetailed[]>;
  getProblem(slug: string): Promise<ProblemDetailed>;
  createProblem(data: Record<string, unknown>): Promise<ProblemDetailed>;
  updateProblem(slug: string, data: Record<string, unknown>): Promise<ProblemDetailed>;
  deleteProblem(slug: string): Promise<void>;
  testProblem(data: Record<string, unknown>): Promise<TestExecutionResult>;

  // Problem Sets
  getProblemSets(): Promise<ProblemSet[]>;
  getProblemSet(slug: string): Promise<ProblemSet>;
  createProblemSet(data: Record<string, unknown>): Promise<ProblemSet>;
  updateProblemSet(slug: string, data: Record<string, unknown>): Promise<ProblemSet>;
  deleteProblemSet(slug: string): Promise<void>;

  // Categories (admin-only, but interface is consistent)
  getCategories(): Promise<ProblemCategory[]>;
  createCategory(data: { name: string; color?: string; description?: string }): Promise<ProblemCategory>;

  // Hints
  getProblemHints(slug: string): Promise<HintConfig[]>;
  updateHints(slug: string, hints: HintConfig[]): Promise<{ problem_slug: string; hints: Array<HintConfig & { created: boolean }> }>;

  // Courses
  getCourses(): Promise<Course[]>;
  getCourse(courseId: string): Promise<Course>;
  createCourse(data: Record<string, unknown>): Promise<Course>;
  updateCourse(courseId: string, data: Record<string, unknown>): Promise<Course>;
  deleteCourse(courseId: string): Promise<void>;

  // Course Students
  getCourseStudents(courseId: string): Promise<CourseStudent[]>;
  removeCourseStudent(courseId: string, userId: number): Promise<void>;

  // Course Problem Sets
  getCourseProblemSets(courseId: string): Promise<CourseProblemSet[]>;
  addCourseProblemSet(courseId: string, data: Record<string, unknown>): Promise<CourseProblemSet>;
  updateCourseProblemSet(courseId: string, membershipId: number, data: Record<string, unknown>): Promise<CourseProblemSet>;
  removeCourseProblemSet(courseId: string, membershipId: number): Promise<void>;
  reorderCourseProblemSets(courseId: string, orderedIds: number[]): Promise<void>;
  getAvailableProblemSetsForCourse(courseId: string): Promise<ProblemSet[]>;

  // Instructors (for admin course assignment)
  getInstructors(): Promise<Instructor[]>;

  // Course Team (multi-instructor management)
  getCourseTeam(courseId: string): Promise<CourseInstructorMember[]>;
  addCourseTeamMember(courseId: string, data: { email: string; role: CourseInstructorRole }): Promise<CourseInstructorMember>;
  updateCourseTeamMember(courseId: string, userId: number, data: { role: CourseInstructorRole }): Promise<CourseInstructorMember>;
  removeCourseTeamMember(courseId: string, userId: number): Promise<void>;

  // Submissions
  getSubmissions(params: SubmissionQueryParams): Promise<PaginatedSubmissions>;
  getSubmission(id: number, courseId?: string): Promise<SubmissionDetailed>;
  exportSubmissions(params: SubmissionQueryParams): Promise<Blob>;

  // Metadata
  readonly baseURL: string;
  readonly role: ContentRole;
}

/**
 * Content Service Implementation
 *
 * Provides all content management operations with role-aware endpoints.
 */
class ContentServiceImpl implements ContentApiService {
  readonly baseURL: string;
  readonly role: ContentRole;

  constructor(role: ContentRole) {
    this.role = role;
    this.baseURL = `/api/${role}`;
  }

  // ============ PROBLEMS ============

  async getProblems(): Promise<ProblemDetailed[]> {
    try {
      const response: AxiosResponse<ProblemDetailed[]> = await axios.get(
        `${this.baseURL}/problems/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load problems');
    }
  }

  async getProblem(slug: string): Promise<ProblemDetailed> {
    try {
      const response: AxiosResponse<ProblemDetailed> = await axios.get(
        `${this.baseURL}/problems/${slug}/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load problem: ${slug}`);
    }
  }

  async createProblem(data: Record<string, unknown>): Promise<ProblemDetailed> {
    try {
      const response: AxiosResponse<ProblemDetailed> = await axios.post(
        `${this.baseURL}/problems/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create problem');
    }
  }

  async updateProblem(slug: string, data: Record<string, unknown>): Promise<ProblemDetailed> {
    try {
      const response: AxiosResponse<ProblemDetailed> = await axios.put(
        `${this.baseURL}/problems/${slug}/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to update problem: ${slug}`);
    }
  }

  async deleteProblem(slug: string): Promise<void> {
    try {
      await axios.delete(`${this.baseURL}/problems/${slug}/`);
    } catch (error) {
      throw this._handleError(error, `Failed to delete problem: ${slug}`);
    }
  }

  async testProblem(data: Record<string, unknown>): Promise<TestExecutionResult> {
    try {
      const response: AxiosResponse<TestExecutionResult> = await axios.post(
        `${this.baseURL}/test-problem/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to test problem solution');
    }
  }

  // ============ PROBLEM SETS ============

  async getProblemSets(): Promise<ProblemSet[]> {
    try {
      const response: AxiosResponse<ProblemSet[]> = await axios.get(
        `${this.baseURL}/problem-sets/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load problem sets');
    }
  }

  async getProblemSet(slug: string): Promise<ProblemSet> {
    try {
      const response: AxiosResponse<ProblemSet> = await axios.get(
        `${this.baseURL}/problem-sets/${slug}/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load problem set: ${slug}`);
    }
  }

  async createProblemSet(data: Record<string, unknown>): Promise<ProblemSet> {
    try {
      const response: AxiosResponse<ProblemSet> = await axios.post(
        `${this.baseURL}/problem-sets/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create problem set');
    }
  }

  async updateProblemSet(slug: string, data: Record<string, unknown>): Promise<ProblemSet> {
    try {
      const response: AxiosResponse<ProblemSet> = await axios.put(
        `${this.baseURL}/problem-sets/${slug}/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to update problem set: ${slug}`);
    }
  }

  async deleteProblemSet(slug: string): Promise<void> {
    try {
      await axios.delete(`${this.baseURL}/problem-sets/${slug}/`);
    } catch (error) {
      throw this._handleError(error, `Failed to delete problem set: ${slug}`);
    }
  }

  // ============ CATEGORIES ============

  async getCategories(): Promise<ProblemCategory[]> {
    try {
      // Categories are always fetched from admin endpoint (shared resource)
      const response: AxiosResponse<ProblemCategory[]> = await axios.get(
        '/api/admin/categories/'
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load categories');
    }
  }

  async createCategory(data: { name: string; color?: string; description?: string }): Promise<ProblemCategory> {
    try {
      // Categories are always created via admin endpoint
      const response: AxiosResponse<ProblemCategory> = await axios.post(
        '/api/admin/categories/',
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create category');
    }
  }

  // ============ HINTS ============

  async getProblemHints(slug: string): Promise<HintConfig[]> {
    try {
      const response = await axios.get(`${this.baseURL}/problems/${slug}/hints/`);
      return response.data.hints || [];
    } catch (error) {
      // If hints endpoint doesn't exist yet, return empty array
      const axiosError = error as { response?: { status: number } };
      if (axiosError.response?.status === 404) {
        return [];
      }
      throw this._handleError(error, `Failed to get hints for problem: ${slug}`);
    }
  }

  async updateHints(slug: string, hints: HintConfig[]): Promise<{
    problem_slug: string;
    hints: Array<HintConfig & { created: boolean }>;
  }> {
    try {
      const response = await axios.put(
        `${this.baseURL}/problems/${slug}/hints/`,
        { hints }
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to update hints for problem: ${slug}`);
    }
  }

  // ============ COURSES ============

  async getCourses(): Promise<Course[]> {
    try {
      const response: AxiosResponse<Course[]> = await axios.get(
        `${this.baseURL}/courses/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load courses');
    }
  }

  async getCourse(courseId: string): Promise<Course> {
    try {
      const response: AxiosResponse<Course> = await axios.get(
        `${this.baseURL}/courses/${courseId}/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load course: ${courseId}`);
    }
  }

  async createCourse(data: Record<string, unknown>): Promise<Course> {
    try {
      // Instructor creates via specific endpoint
      const endpoint = this.role === 'instructor'
        ? `${this.baseURL}/courses/create/`
        : `${this.baseURL}/courses/`;
      const response: AxiosResponse<Course> = await axios.post(endpoint, data);
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to create course');
    }
  }

  async updateCourse(courseId: string, data: Record<string, unknown>): Promise<Course> {
    try {
      const response: AxiosResponse<Course> = await axios.put(
        `${this.baseURL}/courses/${courseId}/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to update course: ${courseId}`);
    }
  }

  async deleteCourse(courseId: string): Promise<void> {
    try {
      await axios.delete(`${this.baseURL}/courses/${courseId}/`);
    } catch (error) {
      throw this._handleError(error, `Failed to delete course: ${courseId}`);
    }
  }

  // ============ COURSE STUDENTS ============

  async getCourseStudents(courseId: string): Promise<CourseStudent[]> {
    try {
      const response: AxiosResponse<CourseStudent[]> = await axios.get(
        `${this.baseURL}/courses/${courseId}/students/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load students for course: ${courseId}`);
    }
  }

  async removeCourseStudent(courseId: string, userId: number): Promise<void> {
    try {
      await axios.delete(
        `${this.baseURL}/courses/${courseId}/students/${userId}/`
      );
    } catch (error) {
      throw this._handleError(error, 'Failed to remove student from course');
    }
  }

  // ============ COURSE PROBLEM SETS ============

  async getCourseProblemSets(courseId: string): Promise<CourseProblemSet[]> {
    try {
      const response: AxiosResponse<CourseProblemSet[]> = await axios.get(
        `${this.baseURL}/courses/${courseId}/problem-sets/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load problem sets for course: ${courseId}`);
    }
  }

  async addCourseProblemSet(courseId: string, data: Record<string, unknown>): Promise<CourseProblemSet> {
    try {
      const response: AxiosResponse<CourseProblemSet> = await axios.post(
        `${this.baseURL}/courses/${courseId}/problem-sets/manage/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to add problem set to course');
    }
  }

  async updateCourseProblemSet(
    courseId: string,
    membershipId: number,
    data: Record<string, unknown>
  ): Promise<CourseProblemSet> {
    try {
      const response: AxiosResponse<CourseProblemSet> = await axios.patch(
        `${this.baseURL}/courses/${courseId}/problem-sets/${membershipId}/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to update course problem set');
    }
  }

  async removeCourseProblemSet(courseId: string, membershipId: number): Promise<void> {
    try {
      await axios.delete(
        `${this.baseURL}/courses/${courseId}/problem-sets/${membershipId}/`
      );
    } catch (error) {
      throw this._handleError(error, 'Failed to remove problem set from course');
    }
  }

  async reorderCourseProblemSets(courseId: string, orderedIds: number[]): Promise<void> {
    try {
      await axios.post(
        `${this.baseURL}/courses/${courseId}/problem-sets/reorder/`,
        { order: orderedIds }
      );
    } catch (error) {
      throw this._handleError(error, 'Failed to reorder course problem sets');
    }
  }

  async getAvailableProblemSetsForCourse(courseId: string): Promise<ProblemSet[]> {
    try {
      const response: AxiosResponse<ProblemSet[]> = await axios.get(
        `${this.baseURL}/courses/${courseId}/available-problem-sets/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load available problem sets');
    }
  }

  // ============ INSTRUCTORS ============

  async getInstructors(): Promise<Instructor[]> {
    try {
      // Instructors list is only available for admin (for course assignment)
      const response: AxiosResponse<Instructor[]> = await axios.get(
        '/api/admin/instructors/'
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load instructors');
    }
  }

  // ============ COURSE TEAM ============

  async getCourseTeam(courseId: string): Promise<CourseInstructorMember[]> {
    try {
      const response: AxiosResponse<CourseInstructorMember[]> = await axios.get(
        `/api/instructor/courses/${courseId}/team/`
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load course team');
    }
  }

  async addCourseTeamMember(
    courseId: string,
    data: { email: string; role: CourseInstructorRole }
  ): Promise<CourseInstructorMember> {
    try {
      const response: AxiosResponse<CourseInstructorMember> = await axios.post(
        `/api/instructor/courses/${courseId}/team/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to add team member');
    }
  }

  async updateCourseTeamMember(
    courseId: string,
    userId: number,
    data: { role: CourseInstructorRole }
  ): Promise<CourseInstructorMember> {
    try {
      const response: AxiosResponse<CourseInstructorMember> = await axios.patch(
        `/api/instructor/courses/${courseId}/team/${userId}/`,
        data
      );
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to update team member');
    }
  }

  async removeCourseTeamMember(courseId: string, userId: number): Promise<void> {
    try {
      await axios.delete(
        `/api/instructor/courses/${courseId}/team/${userId}/`
      );
    } catch (error) {
      throw this._handleError(error, 'Failed to remove team member');
    }
  }

  // ============ SUBMISSIONS ============

  async getSubmissions(params: SubmissionQueryParams): Promise<PaginatedSubmissions> {
    try {
      const queryParams = new URLSearchParams();

      if (params.page) {queryParams.append('page', params.page.toString());}
      if (params.page_size) {queryParams.append('page_size', params.page_size.toString());}
      if (params.search) {queryParams.append('search', params.search);}
      if (params.status) {queryParams.append('status', params.status);}
      if (params.problem_set) {queryParams.append('problem_set', params.problem_set);}

      let url: string;
      if (this.role === 'admin') {
        // Admin can view all submissions, optionally filtered by course
        if (params.course) {queryParams.append('course', params.course);}
        url = `/api/admin/submissions/?${queryParams.toString()}`;
      } else {
        // Instructor must scope to a specific course
        if (!params.course_id) {
          throw new Error('course_id is required for instructor submissions');
        }
        url = `/api/instructor/courses/${params.course_id}/submissions/?${queryParams.toString()}`;
      }

      const response: AxiosResponse<PaginatedSubmissions> = await axios.get(url);
      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to load submissions');
    }
  }

  async getSubmission(id: number, courseId?: string): Promise<SubmissionDetailed> {
    try {
      let url: string;
      if (this.role === 'admin') {
        url = `/api/admin/submissions/${id}/`;
      } else {
        if (!courseId) {
          throw new Error('courseId is required for instructor submission detail');
        }
        url = `/api/instructor/courses/${courseId}/submissions/${id}/`;
      }

      const response: AxiosResponse<SubmissionDetailed> = await axios.get(url);
      return response.data;
    } catch (error) {
      throw this._handleError(error, `Failed to load submission: ${id}`);
    }
  }

  async exportSubmissions(params: SubmissionQueryParams): Promise<Blob> {
    try {
      // Export is admin-only functionality
      if (this.role !== 'admin') {
        throw new Error('CSV export is only available for administrators');
      }

      const response = await axios.post('/api/admin/submissions/', {
        filters: {
          search: params.search || undefined,
          status: params.status || undefined,
          problem_set: params.problem_set || undefined,
          course: params.course || undefined
        },
        format: 'csv'
      }, {
        responseType: 'blob'
      });

      return response.data;
    } catch (error) {
      throw this._handleError(error, 'Failed to export submissions');
    }
  }

  // ============ ERROR HANDLING ============

  private _handleError(error: unknown, defaultMessage: string): APIError {
    const axiosError = error as {
      response?: {
        status: number;
        data?: { error?: string; detail?: string; details?: unknown } & Record<string, unknown>;
      };
      request?: unknown;
      message?: string;
    };

    if (axiosError.response) {
      const { response } = axiosError;

      // Handle validation errors from Django REST framework
      if (response.status === 400 && response.data && typeof response.data === 'object') {
        const validationErrors: string[] = [];
        for (const [field, messages] of Object.entries(response.data)) {
          if (Array.isArray(messages)) {
            validationErrors.push(`${field}: ${messages.join(', ')}`);
          } else if ((field === 'error' || field === 'detail') && typeof messages === 'string') {
            validationErrors.push(messages);
          }
        }

        if (validationErrors.length > 0) {
          return {
            error: validationErrors.join('; '),
            details: response.data,
            status: response.status
          };
        }
      }

      return {
        error: response.data?.error || response.data?.detail || defaultMessage,
        details: response.data?.details,
        status: response.status
      };
    } else if (axiosError.request) {
      return {
        error: 'Network error - please check your connection',
        status: 0
      };
    } else {
      return {
        error: axiosError.message || defaultMessage,
        status: -1
      };
    }
  }
}

// ============ FACTORY & SINGLETONS ============

/**
 * Create a content service for a specific role.
 * @param role - 'admin' for global access, 'instructor' for ownership-scoped
 */
export function createContentService(role: ContentRole): ContentApiService {
  return new ContentServiceImpl(role);
}

// Pre-configured singleton instances for convenience
export const adminContentService = createContentService('admin');
export const instructorContentService = createContentService('instructor');

export default { adminContentService, instructorContentService, createContentService };
