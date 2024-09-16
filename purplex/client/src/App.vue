<template>

    <h1 style="display: inline-flex; text-align: center; gap: 10px; margin: 5px; font-size: 80px;">
        <img src="/vite.png" alt="Purplex Logo" style="width: 100px; height: 100px; margin-right: 10px;" />
        Purplex
    </h1>
    <Login v-if="!loggedIn" />
    <div v-else>
        <NavBar/>
        <router-view />
    </div>

</template>

<script lang="ts">

import { ref } from 'vue';
import problems from './data/problems.json'

/* Components */
import Editor from './components/Editor.vue'
import Feedback from "./components/Feedback.vue"
import Login from './components/Login.vue';
import NavBar from './components/NavBar.vue';
import Home from './components/Home.vue';
import About from './components/About.vue';
import Contact from './components/Contact.vue';
import ProblemSet from './components/ProblemSet.vue';

import AccountModal from './modals/AccountModal.vue';

export default {
    components: {
        Login,
        NavBar,
        Home,
        About,
        Contact,
        Editor,
        Feedback,
        AccountModal,
        ProblemSet
    },
    /*
    methods: {
        getProblem: function () {
            return problems[this.problemIndex];
        },
        updateSolutionCode: function () {
            this.solutionCode = this.getProblem().solution;
            this.codeResults = [];
            this.testResults = [];
            this.promptCorrectness = 0;
        }
    },*/
    computed: {
        loggedIn: function () {
            return this.$store.state.auth.status.loggedIn;
        },
        user: function () {
            return this.$store.state.auth.user;
        }
    }
}

</script>

<style>
.terms li {
    list-style: none;
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding-left: 0;
}

/* place feedback space and entry space side by side */
.workspace {
    display: flex;
    justify-content: space-between;
    gap: 20px;
}

.entryspace {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.entry {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.buttons {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.button {
    color: white;
    border: none;
    padding: 10px 20px;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}

/* add a border around the editor */
.ace_editor {
    border-radius: 5px;
}

/* while waiting for get results  show a spinner */
.bouncing-dots .dot {
    height: 10px;
    width: 10px;
    background-color: #800080;
    border-radius: 50%;
    display: inline-block;
    animation: bounce 1.4s infinite ease-in-out both;
}

.bouncing-dots .dot:nth-child(1) {
    animation-delay: -0.32s;
}

.bouncing-dots .dot:nth-child(2) {
    animation-delay: -0.16s;
}

@keyframes bounce {

    0%,
    80%,
    100% {
        transform: scale(0);
    }

    40% {
        transform: scale(1.0);
    }
}


.spinner {
    border: 16px solid #f3f3f3;
    border-top: 16px solid #3498db;
    border-radius: 50%;
    width: 120px;
    height: 120px;
    animation: spin 2s linear;
}

.divider {
    border-top: 3px solid #1a1a1a;
}
</style>
