<template>
    <div>
        <div class="gallery-title-container">
            <div class="gallery-title">
              Explain in Plain Language Questions
            </div>
            <button v-if="isAdmin" @click="showAddProblemSetModal = true" class="add-btn">
                + Add Problem Set
            </button>
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
        <div class="gallery-title-container">
            <div class="gallery-title">
              Function ReDefinition Questions
            </div>
            <button v-if="isAdmin" @click="showAddProblemSetModal = true" class="add-btn">
                + Add Problem Set
            </button>
        </div>
        <p style="text-align: left;">
            <h3>
            ✨ Coming soon... ✨
            </h3>
        </p>
        
        <!-- Add Problem Set Modal -->
        <div v-if="showAddProblemSetModal" class="modal-backdrop">
            <div class="modal-content">
                <h2>Add New Problem Set</h2>
                <form @submit.prevent="createProblemSet">
                    <div class="form-group">
                        <label for="title">Title:</label>
                        <input type="text" id="title" v-model="newProblemSet.title" required>
                    </div>
                    <div class="form-group">
                        <label for="sid">Set ID (unique identifier):</label>
                        <input type="text" id="sid" v-model="newProblemSet.sid" required>
                    </div>
                    <div class="form-group">
                        <label for="description">Description:</label>
                        <textarea id="description" v-model="newProblemSet.description" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label for="icon">Icon:</label>
                        <input type="file" id="icon" @change="handleFileUpload" accept="image/*">
                    </div>
                    <div class="modal-actions">
                        <button type="button" @click="showAddProblemSetModal = false" class="cancel-btn">Cancel</button>
                        <button type="submit" class="submit-btn">Create Problem Set</button>
                    </div>
                </form>
            </div>
        </div>
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
                },
                showAddProblemSetModal: false,
                newProblemSet: {
                    title: '',
                    sid: '',
                    description: '',
                    icon: null
                }
            };
        },
        computed: {
            isAdmin() {
                return this.$store.getters['auth/isAdmin'];
            }
        },
        methods: {
            handleClick(problemSet) {
                this.$router.push({ path: `/problem-set/${problemSet.sid}`});
                console.log('Problem clicked:', problemSet);
            },
            handleFileUpload(event) {
                this.newProblemSet.icon = event.target.files[0];
            },
            createProblemSet() {
                // Create FormData object to send form including the file
                const formData = new FormData();
                formData.append('title', this.newProblemSet.title);
                formData.append('sid', this.newProblemSet.sid);
                // Empty problems array as required by the serializer
                formData.append('problems', JSON.stringify([]));
                if (this.newProblemSet.icon) {
                    formData.append('icon', this.newProblemSet.icon);
                }
                
                // Log what we're sending for debugging
                console.log('Creating problem set with:', {
                    title: this.newProblemSet.title,
                    sid: this.newProblemSet.sid,
                    problems: [],
                    icon: this.newProblemSet.icon ? this.newProblemSet.icon.name : 'No icon uploaded'
                });
                
                // Always use debug token in development
                const authToken = 'debug';
                console.log('Using auth token:', authToken);
                
                // Send request to create the problem set - remove Content-Type header to allow browser to set it with boundary
                fetch('http://localhost:8000/api/admin/problem-sets/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                })
                .then(response => {
                    if (!response.ok) {
                        // Get the detailed error message from the response
                        return response.json().then(errData => {
                            console.error('Server error details:', errData);
                            throw new Error(`Failed to create problem set: ${JSON.stringify(errData)}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Problem set created successfully:', data);
                    // Add the new problem set to the list
                    this.problemsSets.push(data);
                    // Reset form and close modal
                    this.resetForm();
                    this.showAddProblemSetModal = false;
                })
                .catch(error => {
                    console.error('Error creating problem set:', error);
                    alert(`Failed to create problem set: ${error.message}`);
                });
            },
            resetForm() {
                this.newProblemSet = {
                    title: '',
                    sid: '',
                    description: '',
                    icon: null
                };
            }
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

.gallery-title-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #1f1f1f;
    padding: 0.5rem;
}

.gallery-title {
    font-weight: bold;
    /* make the text left justified */
    text-align: left;
    font-size: larger;
}

.add-btn {
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    cursor: pointer;
    font-weight: bold;
}

.add-btn:hover {
    background-color: #45a049;
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

/* Modal styles */
.modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 100;
}

.modal-content {
    background-color: #2c2c2c;
    border-radius: 8px;
    padding: 20px;
    width: 90%;
    max-width: 500px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.form-group {
    margin-bottom: 15px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
    text-align: left;
}

.form-group input, 
.form-group textarea {
    width: 100%;
    padding: 8px;
    border: 1px solid #444;
    border-radius: 4px;
    background-color: #333;
    color: white;
}

.modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
}

.cancel-btn {
    background-color: #555;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    cursor: pointer;
}

.submit-btn {
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    cursor: pointer;
}

.cancel-btn:hover {
    background-color: #444;
}

.submit-btn:hover {
    background-color: #45a049;
}

</style>
