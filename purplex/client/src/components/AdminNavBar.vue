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
    background-color: #222;
    color: white;
    display: flex;
    justify-content: center;
    width: 100%;
    padding: 10px 0;
    margin-bottom: 20px;
}

.admin-nav-list {
    display: flex;
    justify-content: center;
    gap: 30px;
    list-style: none;
    padding: 0;
    margin: 0;
    width: 100%;
}

.admin-nav-list li {
    display: inline;
}

.admin-link {
    color: white;
    text-decoration: none;
    padding: 8px 12px;
    border-radius: 4px;
    transition: background-color 0.2s;
}

.admin-link:hover, .admin-link.router-link-active {
    background-color: #dc3545;
}

.return-link {
    background-color: #495057;
}
</style>
