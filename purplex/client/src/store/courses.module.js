import axios from 'axios'

export const courses = {
  namespaced: true,
  
  state: {
    // Core course data
    enrolledCourses: [],        // Array of courses user is enrolled in
    availableProblemSets: [],   // Problem sets for browsing when adding to course
    currentCourse: null,        // Active course being viewed
    courseProgress: {},         // Progress keyed by course_id
    
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
      enrollment: false,
      progress: false
    }
  },
  
  getters: {
    // Check enrollment status
    isEnrolledInCourse: (state) => (courseId) => {
      return state.enrolledCourses.some(c => c.course.course_id === courseId)
    },
    
    // Get progress for specific course
    getCourseProgress: (state) => (courseId) => {
      return state.courseProgress[courseId] || { 
        completed_sets: 0, 
        total_sets: 0,
        percentage: 0,
        last_activity: null
      }
    },
    
    // Get problem sets for current course
    getCurrentCourseProblemSets: (state) => {
      if (!state.currentCourse) return []
      return state.currentCourse.problem_sets || []
    },
    
    // Check if user is instructor of any course
    isInstructor: (state, getters, rootState) => {
      return rootState.auth.user?.role === 'instructor' || 
             rootState.auth.user?.role === 'admin'
    },
    
    // Get organized courses by completion status
    organizedCourses: (state, getters) => {
      return {
        active: state.enrolledCourses.filter(c => {
          const progress = c.progress || getters.getCourseProgress(c.course.course_id)
          return progress.percentage < 100
        }),
        completed: state.enrolledCourses.filter(c => {
          const progress = c.progress || getters.getCourseProgress(c.course.course_id)
          return progress.percentage === 100
        })
      }
    }
  },
  
  mutations: {
    // Course data mutations
    SET_ENROLLED_COURSES(state, courses) {
      state.enrolledCourses = courses
    },
    
    ADD_ENROLLED_COURSE(state, courseData) {
      state.enrolledCourses.push(courseData)
    },
    
    SET_CURRENT_COURSE(state, course) {
      state.currentCourse = course
    },
    
    // Progress mutations
    SET_COURSE_PROGRESS(state, { courseId, progress }) {
      state.courseProgress = {
        ...state.courseProgress,
        [courseId]: progress
      }
    },
    
    UPDATE_PROBLEM_SET_PROGRESS(state, { courseId, problemSetId, completed }) {
      if (state.courseProgress[courseId]) {
        if (completed) {
          state.courseProgress[courseId].completed_sets += 1
        }
        const total = state.courseProgress[courseId].total_sets
        const completed_sets = state.courseProgress[courseId].completed_sets
        state.courseProgress[courseId].percentage = 
          Math.round((completed_sets / total) * 100)
      }
    },
    
    // Enrollment modal mutations
    SET_ENROLLMENT_MODAL(state, data) {
      state.enrollmentModal = { ...state.enrollmentModal, ...data }
    },
    
    RESET_ENROLLMENT_MODAL(state) {
      state.enrollmentModal = {
        visible: false,
        loading: false,
        coursePreview: null,
        error: null
      }
    },
    
    // Instructor mutations
    SET_INSTRUCTOR_COURSES(state, courses) {
      state.instructorCourses = courses
    },
    
    SET_STUDENT_PROGRESS(state, { courseId, progress }) {
      state.studentProgress = {
        ...state.studentProgress,
        [courseId]: progress
      }
    },
    
    // Loading state mutations
    SET_LOADING(state, { key, value }) {
      state.loading[key] = value
    }
  },
  
  actions: {
    // Initialize course data on app load
    async initializeCourses({ dispatch, rootGetters }) {
      if (rootGetters['auth/isLoggedIn']) {
        await Promise.all([
          dispatch('fetchEnrolledCourses'),
          dispatch('fetchCourseProgress')
        ])
        
        if (rootGetters['auth/isInstructor']) {
          await dispatch('fetchInstructorCourses')
        }
      }
    },
    
    // Fetch user's enrolled courses
    async fetchEnrolledCourses({ commit }) {
      commit('SET_LOADING', { key: 'courses', value: true })
      try {
        const response = await axios.get('/api/courses/enrolled/')
        commit('SET_ENROLLED_COURSES', response.data)
        return response.data
      } catch (error) {
        console.error('Failed to fetch enrolled courses:', error)
        throw error
      } finally {
        commit('SET_LOADING', { key: 'courses', value: false })
      }
    },
    
    // Fetch progress for all courses
    async fetchCourseProgress({ commit, state }) {
      commit('SET_LOADING', { key: 'progress', value: true })
      try {
        const response = await axios.get('/api/progress/')
        // Transform progress data into course-keyed object
        const progressByCourse = {}
        if (response.data.courses) {
          Object.entries(response.data.courses).forEach(([courseId, courseProgress]) => {
            progressByCourse[courseId] = courseProgress
          })
        }
        
        // Set progress for each course
        Object.keys(progressByCourse).forEach(courseId => {
          commit('SET_COURSE_PROGRESS', { 
            courseId, 
            progress: progressByCourse[courseId] 
          })
        })
      } catch (error) {
        console.error('Failed to fetch course progress:', error)
      } finally {
        commit('SET_LOADING', { key: 'progress', value: false })
      }
    },
    
    // Course enrollment flow
    async lookupCourse({ commit }, courseId) {
      commit('SET_ENROLLMENT_MODAL', { loading: true, error: null })
      
      try {
        const response = await axios.post('/api/courses/lookup/', { 
          course_id: courseId 
        })
        commit('SET_ENROLLMENT_MODAL', { 
          coursePreview: response.data,
          loading: false 
        })
        return response.data
      } catch (error) {
        const errorMsg = error.response?.data?.error || 'Course not found'
        commit('SET_ENROLLMENT_MODAL', { 
          error: errorMsg,
          loading: false,
          coursePreview: null
        })
        throw error
      }
    },
    
    async enrollInCourse({ commit, dispatch }, courseId) {
      commit('SET_ENROLLMENT_MODAL', { loading: true })
      
      try {
        const response = await axios.post('/api/courses/enroll/', { 
          course_id: courseId 
        })
        
        // Refresh enrolled courses
        await dispatch('fetchEnrolledCourses')
        
        // Reset modal
        commit('RESET_ENROLLMENT_MODAL')
        
        // Refresh progress
        await dispatch('fetchCourseProgress')
        
        return response.data
      } catch (error) {
        const errorMsg = error.response?.data?.error || 'Enrollment failed'
        commit('SET_ENROLLMENT_MODAL', { error: errorMsg, loading: false })
        throw error
      }
    },
    
    // Navigate to course context
    async enterCourseContext({ commit }, courseId) {
      try {
        const response = await axios.get(`/api/courses/${courseId}/`)
        commit('SET_CURRENT_COURSE', response.data)
        return response.data
      } catch (error) {
        console.error('Failed to load course:', error)
        throw error
      }
    },
    
    // Leave course context (back to home)
    leaveCourseContext({ commit }) {
      commit('SET_CURRENT_COURSE', null)
    },
    
    // Instructor actions
    async fetchInstructorCourses({ commit }) {
      try {
        const response = await axios.get('/api/instructor/courses/')
        commit('SET_INSTRUCTOR_COURSES', response.data)
        return response.data
      } catch (error) {
        console.error('Failed to fetch instructor courses:', error)
        throw error
      }
    },
    
    async fetchStudentProgress({ commit }, courseId) {
      try {
        const response = await axios.get(
          `/api/instructor/courses/${courseId}/progress/`
        )
        commit('SET_STUDENT_PROGRESS', { courseId, progress: response.data })
        return response.data
      } catch (error) {
        console.error('Failed to fetch student progress:', error)
        throw error
      }
    },
    
    // Show/hide enrollment modal
    showEnrollmentModal({ commit }) {
      commit('SET_ENROLLMENT_MODAL', { visible: true })
    },
    
    hideEnrollmentModal({ commit }) {
      commit('RESET_ENROLLMENT_MODAL')
    }
  }
}