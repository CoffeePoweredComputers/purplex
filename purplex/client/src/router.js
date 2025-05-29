import { createWebHistory, createRouter } from "vue-router";
import { firebaseAuth } from "./firebaseConfig";
import store from "./store"; // Import the Vuex store

// Import components from their feature folders
import Home from "./components/Home.vue";
import About from "./components/About.vue";
import Contact from "./components/Contact.vue";
import Login from "./features/auth/Login.vue";
import ProblemSet from "./features/problems/ProblemSet.vue";
import AdminUsers from "./components/AdminUsers.vue";

const routes = [
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
        path: "/about",
        name: "About",
        component: About,
        meta: {requiresAuth: true},
    },
    {
        path: "/contact",
        name: "Contact",
        component: Contact,
        meta: {requiresAuth: true},
    },
    {
        path: "/problem-set/:slug",
        name: "ProblemSet",
        component: ProblemSet,
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
        component: () => import("./components/AdminProblemEditor.vue"),
        meta: {requiresAuth: true, requiresAdmin: true}
    },
    {
        path: "/admin/problems/:slug/edit",
        name: "AdminEditProblem",
        component: () => import("./components/AdminProblemEditor.vue"),
        props: route => ({ problemSlug: route.params.slug }),
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
    }
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to, from, next) => {
    const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
    const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin);
    
    // Use the debug mode from the Vuex store for consistency
    const debugBypassAuth = store.state.auth.debug;
    
    // If not in debug mode, check auth state
    if (!debugBypassAuth && (requiresAuth || requiresAdmin)) {
        // Make sure we have the latest auth state
        await store.dispatch('auth/checkAuthState');
    }
    
    // Use persistent state from Vuex store
    const isAuthenticated = store.getters['auth/isLoggedIn'];
    const isAdmin = store.getters['auth/isAdmin'];
    
    if (requiresAuth && !isAuthenticated && !debugBypassAuth) {
        next("/login");
    } else if (requiresAdmin && !isAdmin && !debugBypassAuth) {
        // Redirect non-admin users trying to access admin routes
        next("/");
    } else {
        next();
    }
});

export default router;
