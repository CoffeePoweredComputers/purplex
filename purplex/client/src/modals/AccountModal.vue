<template>
    <div class="modal-overlay" v-if="isVisible" @click.self="closeModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Account Information</h3>
                <button class="close-button" @click="closeModal">&times;</button>
            </div>
            <table class="info-table">
                <tr>
                    <td class="info-label"><strong>Name:</strong></td>
                    <td class="info-value">{{ $store.state.auth.user.name }}</td>
                </tr>
                <tr>
                    <td class="info-label"><strong>Email:</strong></td>
                    <td class="info-value">{{ $store.state.auth.user.email }}</td>
                </tr>
                <tr>
                    <td class="info-label"><strong>Role:</strong></td>
                    <td class="info-value">{{ $store.state.auth.user.role }}</td>
                </tr>
            </table>
            <div class="modal-footer">
                <button class="logout-button" @click="logout">Logout</button>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
export default {
    name: 'AccountModal',
    props: {
        isVisible: {
            type: Boolean,
            required: true
        }
    },
    methods: {
        logout() {
            this.$store.dispatch('auth/logout');
        },
        closeModal() {
            this.$emit('close');
        }
    }
};
</script>

<style scoped>
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal-content {
    background-color: #333;
    border-radius: 8px;
    text-align: center;
    padding: 15px;
    max-width: 350px;
    width: 100%;
    z-index: 1001;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #1f1f1f;
    padding: 15px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

.modal-title {
    font-size: 1.25rem;
    font-weight: bold;
    color: #fff;
    margin: 0;
}

.close-button {
    background: none;
    border: none;
    color: white;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0px;
}

.modal-body {
    margin: 15px 0;
    list-style: none;
    padding: 0;
    color: #fff;
    font-size: 0.9rem;
}

.modal-footer {
    margin-top: 15px;
}

.logout-button {
    background-color: #ff4d4d;
    border: none;
    border-radius: 4px;
    padding: 8px 15px;
    color: #fff;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

.logout-button:hover {
    background-color: #ff3333;
}

.info-table {
  width: 100%;
  font-size: 1rem;
}

.info-label {
  text-align: left;
  font-weight: bold;
  color: #ddd;
}

.info-value {
  text-align: right;
  color: #fff;
}
</style>