<template>
  <div class="contact-page">
    <!-- Main Contact Card -->
    <div class="contact-section">
      <div class="contact-card">
        <div class="profile-container">
          <img 
            src="https://scholar.googleusercontent.com/citations?view_op=medium_photo&user=hpe-z9YAAAAJ&citpid=6" 
            alt="David H. Smith IV" 
            class="profile-photo"
          />
          <div class="profile-info">
            <h2 class="profile-name">David H. Smith IV</h2>
            <p class="profile-title">Assistant Professor</p>
            <p class="profile-institution">Virginia Tech, Department of Computer Science</p>
            
            <div class="profile-section">
              <h3>About</h3>
              <p>
                David H. Smith IV researches computing education with a focus on AI-assisted
                programming education and automated assessment. His work explores how large 
                language models can evaluate student understanding.
              </p>
            </div>
            
            <div class="profile-section">
              <h3>Research Interests</h3>
              <p>Computing Education, AI-Assisted Programming, Automated Assessment</p>
            </div>
            
            <div class="contact-actions">
              <a href="mailto:dhsmith2@illinois.edu" class="contact-button primary">
                <span class="button-icon">✉️</span>
                Send Email
              </a>
              <a href="https://hamiltonfour.tech" target="_blank" class="contact-button secondary">
                <span class="button-icon">🌐</span>
                Visit Website
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
export default {
  name: 'Contact'
};
</script>

<style scoped>
.contact-page {
  width: 100%;
  margin: 0;
  padding: var(--spacing-xl) 0 0 0;
}

/* Contact Section */
.contact-section {
  padding: 0 0 60px;
}

.contact-card {
  max-width: 900px;
  margin: 0 auto;
  background: var(--color-bg-panel);
  border-radius: calc(var(--radius-lg) + 4px);
  padding: calc(var(--spacing-xl) + 10px) calc(var(--spacing-xxl) + 10px);
  box-shadow: var(--shadow-base);
}

.profile-container {
  display: flex;
  align-items: center;
  gap: calc(var(--spacing-xl) + 10px);
}

.profile-photo {
  width: 150px;
  height: 150px;
  border-radius: var(--radius-circle);
  border: 4px solid var(--color-primary-gradient-start);
  box-shadow: var(--shadow-colored);
  flex-shrink: 0;
}

.profile-info {
  flex: 1;
  text-align: left;
}

.profile-name {
  font-size: var(--font-size-xxl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.profile-title {
  font-size: var(--font-size-md);
  color: var(--color-text-tertiary);
  margin: 0 0 var(--spacing-xs) 0;
}

.profile-institution {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  margin: 0;
}

.profile-section {
  margin-top: var(--spacing-lg);
}

.profile-section h3 {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.profile-section p {
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  line-height: 1.6;
  margin: 0;
}

.contact-actions {
  display: flex;
  gap: var(--spacing-base);
  flex-wrap: wrap;
  margin-top: calc(var(--spacing-lg) + 5px);
}

.contact-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) calc(var(--spacing-lg) + 4px);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  font-weight: 500;
  text-decoration: none;
  transition: var(--transition-base);
  cursor: pointer;
}

.contact-button.primary {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-colored);
}

.contact-button.primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-colored);
}

.contact-button.secondary {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.contact-button.secondary:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.button-icon {
  font-size: 20px;
}

/* Responsive Design */
@media (max-width: 768px) {
  .contact-card {
    padding: var(--spacing-xl) var(--spacing-lg);
  }
  
  .profile-container {
    flex-direction: column;
    text-align: center;
    gap: var(--spacing-lg);
  }
  
  .profile-info {
    text-align: center;
  }
  
  .profile-photo {
    width: 120px;
    height: 120px;
  }
  
  .profile-name {
    font-size: 28px;
  }
  
  .contact-actions {
    flex-direction: column;
    justify-content: center;
  }
  
  .contact-button {
    width: 100%;
    justify-content: center;
  }
}
</style>
