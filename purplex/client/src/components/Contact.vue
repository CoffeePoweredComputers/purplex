<template>
  <div class="publications-list">
    <h1 class="title">Contact</h1>
    
    <ul class="publications">
      <li class="publication-item">
        <span class="name-title">David H. Smith IV</span>
        <span class="publication-meta">Assistant Professor, Virginia Tech, Department of Computer Science</span>
        <span class="publication-actions">
          <button class="btn"><a href="mailto:dhsmith2@illinois.edu">Email</a></button> | 
          <button class="btn"><a href="https://hamiltonfour.tech" target="_blank">Website</a></button>
        </span>
      </li>
      
      <li class="publication-item">
        <span class="publication-title">Research Interests</span>
        <span class="publication-meta">Computing Education, AI-Assisted Programming, Automated Assessment</span>
      </li>
      
      <li class="publication-item">
        <span class="publication-title">About</span>
        <span class="publication-meta">
          David H. Smith IV researches computing education with a focus on AI-assisted
          programming education and automated assessment. His work on code generation-based
          grading explores how large language models can be used to evaluate student 
          understanding in programming courses.
        </span>
      </li>
      
      <li class="publication-item">
        <span class="publication-title">Collaborate</span>
        <span class="publication-meta">
          For questions about Purplex or research collaborations, please reach out via email.
        </span>
      </li>
    </ul>
  </div>
</template>

<script lang="ts">
export default {
  name: 'Contact'
};
</script>

<style scoped>
.publications-list {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

.title {
  margin-bottom: 10px;
}

.scholar-link {
  margin-bottom: 20px;
}

.scholar-link a {
  color: #1a0dab;
  text-decoration: none;
}

.scholar-link a:hover {
  text-decoration: underline;
}

.publications {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.publication-item {
  padding: 12px 0;
  border-bottom: 1px solid #eee;
}

.name-title {
  font-weight: bold;
  display: block;
  margin-bottom: 5px;
  font-size: 1.5em;
}

.publication-title {
  font-weight: bold;
  display: block;
  margin-bottom: 5px;
}

.publication-meta {
  color: #555;
  font-size: 0.9em;
  display: block;
  margin-bottom: 5px;
  line-height: 1.5;
}

.publication-actions {
  font-size: 0.9em;
  display: block;
}

.publication-actions a {
  color: #1a0dab;
  text-decoration: none;
}

.publication-actions a:hover {
  text-decoration: underline;
}

.btn, .btn a {
  background: purple;
  border: none;
  color: white;
  font-weight: bold;
  cursor: pointer;
  font-size: 1em;
  padding: 2px 5px 2px 5px;
  font-family: inherit;
  text-align: center;
}

.btn:hover {
  text-decoration: underline;
}
</style>
