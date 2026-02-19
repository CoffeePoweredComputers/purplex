<template>
  <div class="policy-page">
    <div class="policy-page__content">
      <h1>Privacy Policy</h1>
      <p class="policy-page__version">Version 1.0 — Effective {{ effectiveDate }}</p>

      <section>
        <h2>1. Who We Are</h2>
        <p>
          Purplex is an educational coding challenge platform. We act as a
          <strong>data controller</strong> for direct student signups and as a
          <strong>data processor</strong> for institutional deployments.
        </p>
      </section>

      <section>
        <h2>2. Data We Collect</h2>
        <ul>
          <li><strong>Identity Data:</strong> email, username, name (from registration or Google OAuth)</li>
          <li><strong>Submission Data:</strong> code you write, plain-language explanations</li>
          <li><strong>Progress Data:</strong> scores, attempts, time spent, hints used</li>
          <li><strong>AI Analysis Data:</strong> comprehension analysis of your submissions (with your consent)</li>
          <li><strong>Technical Data:</strong> IP addresses, browser type (from server logs)</li>
        </ul>
      </section>

      <section>
        <h2>3. How We Use Your Data</h2>
        <ul>
          <li>Provide the educational coding platform</li>
          <li>Track your progress and provide feedback</li>
          <li>Generate AI-powered comprehension analysis (with consent)</li>
          <li>Improve the platform through anonymized research (with consent)</li>
        </ul>
      </section>

      <section>
        <h2>4. Third-Party Data Processors</h2>
        <p>With your consent, we share data with:</p>
        <ul>
          <li><strong>Firebase (Google):</strong> Authentication services — your email and display name</li>
          <li><strong>OpenAI:</strong> Your code submissions and explanations for AI analysis</li>
        </ul>
        <p>
          These processors are based in the United States. Data transfers are governed
          by Standard Contractual Clauses and Data Processing Agreements.
        </p>
      </section>

      <section>
        <h2>5. Your Rights</h2>
        <p>Under GDPR, CCPA, and DPDPA, you have the right to:</p>
        <ul>
          <li><strong>Access:</strong> Download all your data (Settings → Privacy)</li>
          <li><strong>Rectification:</strong> Update your profile information</li>
          <li><strong>Erasure:</strong> Delete your account (30-day grace period)</li>
          <li><strong>Portability:</strong> Export your data in JSON format</li>
          <li><strong>Object:</strong> Withdraw consent for AI processing at any time</li>
          <li><strong>Restrict Processing:</strong> Opt out of behavioral tracking</li>
        </ul>
      </section>

      <section>
        <h2>6. Data Retention</h2>
        <ul>
          <li>Submissions: retained for 3 years after course completion</li>
          <li>Progress snapshots: retained for 2 years</li>
          <li>Server logs: 90 days</li>
          <li>Inactive accounts: warning at 12 months, deletion at 24 months</li>
        </ul>
      </section>

      <section>
        <h2>7. Children's Privacy</h2>
        <p>
          Users under 13 (COPPA) require verifiable parental consent.
          Users under 18 in India (DPDPA) have additional protections including
          restrictions on behavioral tracking and AI profiling.
        </p>
      </section>

      <section>
        <h2>8. Do Not Sell or Share</h2>
        <p>
          We do not sell your personal information. When we share data with AI providers
          (OpenAI), this is for service functionality only and requires your explicit consent.
        </p>
      </section>

      <section>
        <h2>9. Cookies</h2>
        <p>
          We use essential cookies for authentication and session management.
          Optional analytics cookies are only set with your consent.
        </p>
      </section>

      <section>
        <h2>10. Contact & Grievance Officer</h2>
        <p>
          For privacy inquiries or to exercise your rights, contact our
          Data Protection Officer / Grievance Officer at the contact information
          provided in your institutional agreement or platform settings.
        </p>
      </section>

      <section>
        <h2>11. Changes to This Policy</h2>
        <p>
          We will notify you of material changes and may request re-consent
          for significant updates to data processing practices.
        </p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
const effectiveDate = new Date().toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
});
</script>

<style scoped>
.policy-page {
    max-width: 800px;
    margin: var(--spacing-xl) auto;
    padding: 0 var(--spacing-xl) var(--spacing-xxl);
}

.policy-page__content {
    color: var(--color-text-secondary);
    line-height: 1.6;
}

.policy-page__version {
    color: var(--color-text-muted);
    font-size: var(--font-size-sm);
    margin-bottom: var(--spacing-xl);
}

.policy-page h1 {
    font-size: var(--font-size-xxl);
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-xs);
}

.policy-page h2 {
    font-size: var(--font-size-md);
    margin-top: var(--spacing-xl);
    margin-bottom: var(--spacing-sm);
    color: var(--color-text-primary);
}

.policy-page section {
    margin-bottom: var(--spacing-base);
}

.policy-page p,
.policy-page li {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

.policy-page ul {
    padding-left: var(--spacing-xl);
}

.policy-page li {
    margin-bottom: var(--spacing-xs);
}

.policy-page a {
    color: var(--color-primary-gradient-start);
}

.policy-page a:hover {
    color: var(--color-primary-gradient-end);
}
</style>
