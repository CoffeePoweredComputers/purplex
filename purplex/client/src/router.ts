import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
import store from "./store"; // Import the Vuex store
import { ensureFirebaseInitialized } from "./firebaseConfig";
import { waitForAuthState } from "./utils/auth-state";

// Eagerly load only critical components
import Login from "./features/auth/Login.vue";

// Lazy load all other components to reduce initial bundle size
const Home = () => import(/* webpackChunkName: "home" */ "./components/Home.vue");
const ProblemSet = () => import(/* webpackChunkName: "problems" */ "./features/problems/ProblemSet.vue");
const AdminUsers = () => import(/* webpackChunkName: "admin" */ "./components/AdminUsers.vue");

const routes: RouteRecordRaw[] = [
    {
        path: "/",
        name: "Login",
        component: Login,
    },
    {
        path: "/home",
        name: "Home",
        component: Home,
        meta: {requiresAuth: true},
    },
    {
        path: "/problem-set/:slug",
        name: "ProblemSet",
        component: ProblemSet,
        meta: {requiresAuth: true}
    },
    // Course routes
    {
        path: "/courses/:courseId",
        name: "CourseDetail",
        component: () => import("./components/CourseDetail.vue"),
        meta: {requiresAuth: true}
    },
    {
        path: "/courses/:courseId/problem-set/:slug",
        name: "CourseProblemSet",
        component: ProblemSet,
        props: route => ({
            slug: route.params.slug as string,
            courseId: route.params.courseId as string
        }),
        meta: {requiresAuth: true}
    },
    // Instructor routes (FERPA-compliant - instructors see only their courses)
    {
        path: "/instructor",
        name: "InstructorDashboard",
        component: () => import("./components/instructor/InstructorDashboard.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/courses/:courseId",
        name: "InstructorCourseOverview",
        component: () => import("./components/instructor/InstructorCourseOverview.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/courses/:courseId/students",
        name: "InstructorStudents",
        component: () => import("./components/instructor/InstructorStudents.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/courses/:courseId/submissions",
        name: "InstructorSubmissions",
        component: () => import("./components/content/SubmissionsPage.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/courses/:courseId/submissions/:submissionId",
        name: "InstructorSubmissionDetail",
        component: () => import("./components/content/SubmissionDetailPage.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    // Instructor Content Management routes - using unified components
    {
        path: "/instructor/problems",
        name: "InstructorProblems",
        component: () => import("./components/content/ProblemList.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/problems/new",
        name: "InstructorCreateProblem",
        component: () => import("./components/content/ProblemEditorShell.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/problems/:slug/edit",
        name: "InstructorEditProblem",
        component: () => import("./components/content/ProblemEditorShell.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/problem-sets",
        name: "InstructorProblemSets",
        component: () => import("./components/content/ProblemSetManager.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/problem-sets/new",
        name: "InstructorCreateProblemSet",
        component: () => import("./components/content/ProblemSetEditorShell.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/problem-sets/:slug/edit",
        name: "InstructorEditProblemSet",
        component: () => import("./components/content/ProblemSetEditorShell.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    // Instructor Course Management
    {
        path: "/instructor/courses",
        name: "InstructorCourses",
        component: () => import("./components/content/CourseList.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/courses/new",
        name: "InstructorCreateCourse",
        component: () => import("./components/content/CourseEditorShell.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/courses/:courseId/edit",
        name: "InstructorEditCourse",
        component: () => import("./components/content/CourseEditorShell.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/courses/:courseId/students",
        name: "InstructorCourseStudents",
        component: () => import("./components/content/CourseStudentsPage.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    {
        path: "/instructor/courses/:courseId/problem-sets",
        name: "InstructorCourseProblemSets",
        component: () => import("./components/content/CourseProblemSetsPage.vue"),
        meta: {requiresAuth: true, requiresInstructor: true}
    },
    // Legacy instructor course create route (redirect to new)
    {
        path: "/instructor/courses/create",
        name: "InstructorCourseCreateLegacy",
        redirect: "/instructor/courses/new"
    },
    // Admin routes
    {
        path: "/admin/users",
        name: "AdminUsers",
        component: AdminUsers,
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    // Admin Content Management routes - using unified components
    {
        path: "/admin/problems",
        name: "AdminProblems",
        component: () => import("./components/content/ProblemList.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problems/new",
        name: "AdminCreateProblem",
        component: () => import("./components/content/ProblemEditorShell.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problems/:slug/edit",
        name: "AdminEditProblem",
        component: () => import("./components/content/ProblemEditorShell.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problem-sets",
        name: "AdminProblemSets",
        component: () => import("./components/content/ProblemSetManager.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problem-sets/new",
        name: "AdminCreateProblemSet",
        component: () => import("./components/content/ProblemSetEditorShell.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problem-sets/:slug/edit",
        name: "AdminEditProblemSet",
        component: () => import("./components/content/ProblemSetEditorShell.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/submissions",
        name: "AdminSubmissions",
        component: () => import("./components/content/SubmissionsPage.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/submissions/:submissionId",
        name: "AdminSubmissionDetail",
        component: () => import("./components/content/SubmissionDetailPage.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/courses/:courseId/submissions",
        name: "AdminCourseSubmissions",
        component: () => import("./components/content/SubmissionsPage.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    // Admin Course Management
    {
        path: "/admin/courses",
        name: "AdminCourses",
        component: () => import("./components/content/CourseList.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/courses/new",
        name: "AdminCreateCourse",
        component: () => import("./components/content/CourseEditorShell.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/courses/:courseId/edit",
        name: "AdminEditCourse",
        component: () => import("./components/content/CourseEditorShell.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/courses/:courseId/students",
        name: "AdminCourseStudents",
        component: () => import("./components/content/CourseStudentsPage.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/courses/:courseId/problem-sets",
        name: "AdminCourseProblemSets",
        component: () => import("./components/content/CourseProblemSetsPage.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    // Privacy & compliance routes (public — no auth required for policy pages)
    {
        path: "/privacy",
        name: "PrivacyPolicy",
        component: () => import("./components/privacy/PrivacyPolicy.vue"),
    },
    {
        path: "/terms",
        name: "TermsOfService",
        component: () => import("./components/privacy/TermsOfService.vue"),
    },
    // Authenticated privacy settings
    {
        path: "/settings/privacy",
        name: "PrivacySettings",
        component: () => import("./components/privacy/PrivacySettings.vue"),
        meta: {requiresAuth: true}
    }
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to, _from, next) => {
    const requiresAuth = to.matched.some(record => record.meta?.requiresAuth);
    const requiresAdmin = to.matched.some(record => record.meta?.requiresAdmin);
    const requiresInstructor = to.matched.some(record => record.meta?.requiresInstructor);

    // Use the debug mode from the Vuex store for consistency
    const debugBypassAuth = store.state.auth.debug;

    // Wait for auth state to be determined
    await waitForAuthState();
    await store.dispatch('auth/checkAuthState');

    // Use persistent state from Vuex store
    const isAuthenticated = store.getters['auth/isLoggedIn'];
    const isAdmin = store.getters['auth/isAdmin'];
    const isInstructor = store.getters['auth/isInstructor'];

    // If user is logged in and trying to access login page, redirect to home
    if (to.path === "/" && isAuthenticated) {
        next("/home");
        return;
    }

    if (requiresAuth && !isAuthenticated && !debugBypassAuth) {
        next("/");
    } else if (requiresAdmin && !isAdmin && !debugBypassAuth) {
        // Redirect non-admin users trying to access admin routes
        next("/");
    } else if (requiresInstructor && !isInstructor && !debugBypassAuth) {
        // Redirect non-instructor users trying to access instructor routes
        // FERPA: Ensure only instructors can access instructor panel
        next("/");
    } else {
        next();
    }
});

export default router;
