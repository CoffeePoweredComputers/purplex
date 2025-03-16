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
import { defineComponent, computed } from 'vue';
import { useStore } from 'vuex';

/* Components */
import Login from './features/auth/Login.vue';
import NavBar from './components/NavBar.vue';

export default defineComponent({
    name: 'App',
    components: {
        Login,
        NavBar
    },
    setup() {
        const store = useStore();
        
        const loggedIn = computed(() => store.state.auth.status.loggedIn);
        const user = computed(() => store.state.auth.user);
        
        return {
            loggedIn,
            user
        };
    }
});
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
