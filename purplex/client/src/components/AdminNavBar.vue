<template>
    <nav class="admin-nav">
        <ul class="admin-nav-list">
            <li><router-link to="/admin/users" class="admin-link">Users</router-link></li>
            <li><router-link to="/admin/problems" class="admin-link">Problems</router-link></li>
            <li><router-link to="/admin/submissions" class="admin-link">Submissions</router-link></li>
        </ul>
    </nav>
</template>

<script>
export default {
    name: "AdminNavBar"
}
</script>

<style scoped>
.admin-nav {
    background-color: var(--color-bg-dark);
    color: var(--color-text-primary);
    display: flex;
    justify-content: center;
    width: 100%;
    padding: var(--spacing-sm) 0;
    margin-bottom: var(--spacing-lg);
}

.admin-nav-list {
    display: flex;
    justify-content: center;
    gap: var(--spacing-xl);
    list-style: none;
    padding: 0;
    margin: 0;
    width: 100%;
}

.admin-nav-list li {
    display: inline;
}

.admin-link {
    color: var(--color-text-primary);
    text-decoration: none;
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-xs);
    transition: background-color var(--transition-fast);
}

.admin-link:hover, .admin-link.router-link-active {
    background-color: var(--color-error);
}

.return-link {
    background-color: var(--color-bg-disabled);
}
</style>
