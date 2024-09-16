<template>
    <div>
        <div class="gallery-title">
            Code Comprehension Questions
        </div>
        <div class="gallery">
            <div v-if="this.loading.codeComprehension"> Loading... </div>
            <div v-else>
                <button class="tile" v-for="problemSet in problemsSets" :key="problemSet.name" @click="handleClick(problemSet)">
                    <div class="image-container">
                        <img :src="problemSet.icon" :alt="problemSet.title" />
                    </div>
                    <div class="title">{{ problemSet.title }}</div>
                </button>
            </div>
        </div>
        <div class="gallery-title">
            Natural Language Programming Problems
        </div>
        <p style="text-align: left;">
            <h3>
            ✨ Coming soon... ✨
            </h3>
        </p>
    </div>
</template>

<script>
    export default {
        name: 'Gallery',
        data() {
            return {
                problemsSets: [],
                loading: {
                    codeComprehension: false,
                }
            };
        },
        methods: {
            handleClick(problemSet) {
                this.$router.push({ path: `/problem-set/${problemSet.sid}`});
                console.log('Problem clicked:', problemSet);
            },
        },
        created() {
            this.loading.codeComprehension = true;
            fetch('http://localhost:8000/api/problem-sets/')
                .then(response => response.json())
                .then(data => {
                    this.problemsSets = data;
                });
            this.loading.codeComprehension = false;
        },
    };
</script>

<style scoped>

.gallery-title {
    font-weight: bold;
    background-color: #1f1f1f;
    padding: 0.5rem;
    /* make the text left justified */
    text-align: left;
    font-size: larger;
}

.gallery {
    display: flex;
    overflow-x: auto;
    gap: 10px;
    padding: 10px;
    height: 200px;
}

.tile {
    border: 1px solid #ccc;
    border-radius: 4px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    cursor: pointer;
    padding: 0;
    text-align: left;
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
    min-width: 50px;
    flex-shrink: 0;
}

.image-container {
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
}

.image-container img {
    width: 150px;
    height: auto;
    display: block;
}

.title {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 10px;
    height: 30px;
    background-color: #7d7d7d;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    font-weight: bolder;
}

.checkmark {
    font-size: 12px;
    color: green;
}

</style>
