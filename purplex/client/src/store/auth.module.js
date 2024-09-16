//import AuthService from '../services/auth.service';
import { firebaseAuth } from '../firebaseConfig';
import { signInWithEmailAndPassword, createUserWithEmailAndPassword } from 'firebase/auth';

const DEBUG = true;

const user = JSON.parse(localStorage.getItem('user'));
const initialState = user
    ? { status: { loggedIn: true }, user }
    : { status: { loggedIn: false }, user: null };

export const auth = {
    namespaced: true,
    state: initialState,
    actions: {
        async login({ commit }, user) {
            if (DEBUG){
                commit('loginSuccess', user);
            }
            else if (await signInWithEmailAndPassword(firebaseAuth, user.email, user.password)) {
                commit('loginSuccess', user);
            } else {
                throw new Error('Invalid credentials.');
            }
        },
        logout({ commit }) {
            commit('logout');
        },
        async createAccount({ commit }, user) {
            const response = await createUserWithEmailAndPassword(firebaseAuth, user.email, user.password);
            if (response) {
                commit('registerSuccess');
            } else {
                throw new Error('Unable to register user.');
            }
        }
    },
    mutations: {
        loginSuccess(state, user) {
            state.status.loggedIn = true;
            state.user = user;
        },
        logout(state) {
            state.status.loggedIn = false;
            state.user = null;
        },
        registerSuccess(state) {
            state.status.loggedIn = false;
        }
    },
    getters: {
        isLoggedIn: state => state.status.loggedIn,
        getUser: state => state.user
    }
};
