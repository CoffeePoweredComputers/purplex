import { createWebHistory, createRouter } from "vue-router";
import { firebaseAuth } from "./firebaseConfig";

import Home from "./components/Home.vue";
import Login from "./components/Login.vue";
import About from "./components/About.vue";
import Contact from "./components/Contact.vue";
import ProblemSet from "./components/ProblemSet.vue";

import Feedback from "./components/Feedback.vue";


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
        path: "/problem-set/:name",
        name: "ProblemSet",
        component: ProblemSet,
        meta: {requiresAuth: true}
    }
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach((to, from, next) => {
    const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
    const isAuthenticated = true; // TODO: remove this after doing debugging stuff
    if (requiresAuth && !isAuthenticated) {
        next("/");
    } else {
        next();
    }
});

export default router;
