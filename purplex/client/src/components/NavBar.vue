<template>
    <nav>
        <ul class="nav-list">
            <li><router-link to="/home"><button>Home</button></router-link></li>
            <li><router-link to="/about"><button>About</button></router-link></li>
            <li><router-link to="/contact"><button>Contact</button></router-link></li>
            <li v-if="isAdmin"><router-link to="/admin/users"><button class="admin-button">Admin</button></router-link></li>
            <li class="account-button"><button @click="showAccountModal = true">Account</button></li>
        </ul>
        <AccountModal :isVisible="showAccountModal" @close="showAccountModal = false" />
    </nav>
</template>

<script lang="ts">
import { mapGetters } from 'vuex';
import AccountModal from '../modals/AccountModal.vue';

export default {
    name: "NavBar",
    components: {
        AccountModal
    },
    data() {
        return {
            showAccountModal: false
        };
    },
    computed: {
        ...mapGetters('auth', ['isAdmin'])
    },
    methods: {
    }
};
</script>

<style scoped>
nav {
    background-color: var(--color-bg-input);
    color: var(--color-text-primary);
    display: flex;
    justify-content: center;
    position: relative;
    width: 100%;
}

.nav-list {
    display: flex;
    justify-content: center;
    gap: var(--spacing-xxl);
    list-style: none;
    padding: 0;
    margin: 0;
    position: relative;
    width: 100%;
}

.nav-list li {
    display: inline;
}

.account-button {
    position: absolute;
    right: 0;
}

button {
    background-color: var(--color-bg-input);
    color: var(--color-text-primary);
    padding: var(--spacing-base) var(--spacing-base);
    margin: 0;
    cursor: pointer;
    border: none;
    border-radius: var(--radius-xs);
    transition: var(--transition-base);
    font-weight: 500;
}

button:hover {
    background-color: var(--color-bg-hover);
}

.admin-button {
    background-color: var(--color-error);
    font-weight: bold;
}

.admin-button:hover {
    background-color: var(--color-error-bg);
    color: var(--color-error-text);
}
</style>
