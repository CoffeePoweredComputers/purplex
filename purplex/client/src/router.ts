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
    // Admin routes
    {
        path: "/admin/users",
        name: "AdminUsers",
        component: AdminUsers,
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problems",
        name: "AdminProblems",
        component: () => import("./components/AdminProblems.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problems/new",
        name: "AdminCreateProblem",
        component: () => import("./components/admin/AdminProblemEditorShell.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problems/:slug/edit",
        name: "AdminEditProblem",
        component: () => import("./components/admin/AdminProblemEditorShell.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problem-sets",
        name: "AdminProblemSets",
        component: () => import("./components/AdminProblemSets.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/submissions",
        name: "AdminSubmissions",
        component: () => import("./components/AdminSubmissions.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/courses",
        name: "AdminCourses",
        component: () => import("./components/AdminCourses.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    }
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to, _from, next) => {
    const requiresAuth = to.matched.some(record => record.meta?.requiresAuth);
    const requiresAdmin = to.matched.some(record => record.meta?.requiresAdmin);

    // Use the debug mode from the Vuex store for consistency
    const debugBypassAuth = store.state.auth.debug;

    // Wait for auth state to be determined
    await waitForAuthState();
    await store.dispatch('auth/checkAuthState');

    // Use persistent state from Vuex store
    const isAuthenticated = store.getters['auth/isLoggedIn'];
    const isAdmin = store.getters['auth/isAdmin'];

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
    } else {
        next();
    }
});

export default router;
