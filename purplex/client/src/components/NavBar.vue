<template>
    <nav>
        <ul class="nav-list">
            <li><router-link to="/home"><button>Home</button></router-link></li>
            <li class="right-buttons">
                <div v-if="isAdmin"><router-link to="/admin/users"><button class="admin-button">Admin</button></router-link></div>
                <div><button @click="showAccountModal = true">Account</button></div>
            </li>
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
    background: var(--color-bg-panel);
    color: var(--color-text-primary);
    display: flex;
    justify-content: center;
    position: sticky;
    top: 0;
    width: 100%;
    z-index: 999;
    box-shadow: var(--shadow-md);
    border-bottom: 2px solid var(--color-bg-input);
}

.nav-list {
    display: flex;
    justify-content: space-between;
    align-items: center;
    list-style: none;
    padding: var(--spacing-sm) var(--spacing-xl);
    margin: 0;
    width: 100%;
    max-width: var(--max-width-content);
}

.nav-list li {
    display: inline-flex;
}

.right-buttons {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

/* Logo/Brand area - using first link as brand */
.nav-list li:first-child {
    /* No special positioning needed with space-between */
}

.nav-list li:first-child button {
    background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
    color: var(--color-text-primary);
    font-weight: 700;
    font-size: var(--font-size-md);
    padding: var(--spacing-sm) var(--spacing-lg);
    box-shadow: var(--shadow-colored);
}

.nav-list li:first-child button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.nav-list li:first-child button::before {
    display: none;
}

button {
    background: transparent;
    color: var(--color-text-secondary);
    padding: var(--spacing-sm) var(--spacing-lg);
    margin: 0;
    cursor: pointer;
    border: 2px solid transparent;
    border-radius: var(--radius-base);
    transition: var(--transition-base);
    font-weight: 600;
    font-size: var(--font-size-base);
    position: relative;
    overflow: hidden;
}

button::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    width: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
    transition: var(--transition-base);
    transform: translateX(-50%);
}

button:hover {
    color: var(--color-text-primary);
    background: var(--color-bg-hover);
    border-color: var(--color-bg-input);
}

button:hover::after {
    width: 80%;
}

/* Active route styling */
.router-link-active button:not(.admin-button) {
    color: var(--color-text-primary);
    background: var(--color-bg-hover);
}

.router-link-active button::after {
    width: 80%;
}

/* Admin button special styling */
.admin-button {
    background: var(--color-admin);
    color: var(--color-text-primary);
    font-weight: 600;
    border: none;
    box-shadow: 0 2px 8px rgba(103, 58, 183, 0.3);
}

.admin-button::before {
    content: "⚙️ ";
}

.admin-button:hover {
    background: var(--color-admin-hover);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(103, 58, 183, 0.4);
}

.admin-button::after {
    display: none;
}

/* Account button styling */
.account-button button {
    background: var(--color-bg-hover);
    border: 2px solid var(--color-bg-input);
}

.account-button button::before {
    display: none;
}

.account-button button:hover {
    background: var(--color-bg-input);
    border-color: var(--color-primary-gradient-start);
    transform: translateY(-1px);
}

/* Mobile responsive */
@media (max-width: 768px) {
    .nav-list {
        padding: var(--spacing-sm) var(--spacing-md);
    }
    
    .right-buttons {
        gap: var(--spacing-sm);
    }
    
    button {
        padding: var(--spacing-sm) var(--spacing-md);
        font-size: var(--font-size-sm);
    }
    
    .nav-list li:first-child button::before,
    .admin-button::before,
    .account-button button::before {
        display: none;
    }
}

/* Smaller mobile */
@media (max-width: 480px) {
    .nav-list {
        gap: var(--spacing-xs);
    }
    
    button {
        padding: var(--spacing-xs) var(--spacing-sm);
    }
}
</style>
