<template>
    <nav>
        <ul class="nav-list">
            <li><router-link to="/home"><button>Home</button></router-link></li>
            <li><router-link to="/about"><button>About</button></router-link></li>
            <li><router-link to="/contact"><button>Contact</button></router-link></li>
            <li class="account-button"><button @click="showAccountModal = true">Account</button></li>
        </ul>
        <AccountModal :isVisible="showAccountModal" @close="showAccountModal = false" />
    </nav>
</template>

<script lang="ts">

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
    methods: {
    }
};
</script>

<style scoped>
nav {
    background-color: #333;
    color: white;
    display: flex;
    justify-content: center;
    position: relative;
    width: 100%;
}

.nav-list {
    display: flex;
    justify-content: center;
    gap: 50px;
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
    background-color: #333;
    color: white;
    padding: 15px 15px;
    margin: 0px;
    cursor: pointer;
}

</style>
