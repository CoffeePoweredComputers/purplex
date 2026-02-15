<template>
  <div class="policy-page">
    <div class="policy-page__content">
      <h1>Terms of Service</h1>
      <p class="policy-page__version">Version 1.0 — Effective {{ effectiveDate }}</p>

      <section>
        <h2>1. Acceptance of Terms</h2>
        <p>
          By creating an account on Purplex, you agree to these Terms of Service
          and our <a href="/privacy">Privacy Policy</a>.
        </p>
      </section>

      <section>
        <h2>2. Service Description</h2>
        <p>
          Purplex is an educational platform for practicing coding challenges.
          The platform includes AI-powered features that analyze code submissions
          for comprehension assessment.
        </p>
      </section>

      <section>
        <h2>3. AI Processing Disclosure</h2>
        <p>
          With your consent, code you submit may be sent to third-party AI services
          (including OpenAI) for analysis. This processing includes:
        </p>
        <ul>
          <li>Generating code variations from natural language descriptions</li>
          <li>Analyzing comprehension levels through segmentation analysis</li>
          <li>Generating educational feedback</li>
        </ul>
        <p>
          You can opt out of AI processing at any time in your Privacy Settings.
          Core platform functionality (submitting code, viewing results) remains
          available without AI processing.
        </p>
      </section>

      <section>
        <h2>4. Age Restrictions</h2>
        <p>
          Users under 13 years of age require verifiable parental consent
          before using this platform. Users under 18 in certain jurisdictions
          may have additional restrictions on data processing.
        </p>
      </section>

      <section>
        <h2>5. User Conduct</h2>
        <p>You agree not to:</p>
        <ul>
          <li>Submit malicious code designed to exploit the execution environment</li>
          <li>Attempt to access other users' data</li>
          <li>Use the platform for purposes unrelated to educational coding practice</li>
          <li>Share your account credentials with others</li>
        </ul>
      </section>

      <section>
        <h2>6. Intellectual Property</h2>
        <p>
          Code you submit remains your intellectual property. By submitting code,
          you grant Purplex a license to process it for the purposes of grading,
          feedback, and (with your consent) research.
        </p>
      </section>

      <section>
        <h2>7. Account Termination</h2>
        <p>
          You may delete your account at any time through Privacy Settings.
          We may suspend accounts that violate these terms.
          See our Privacy Policy for data retention details upon account deletion.
        </p>
      </section>

      <section>
        <h2>8. Limitation of Liability</h2>
        <p>
          Purplex is provided "as is" for educational purposes. We are not liable
          for any loss of data, grades, or academic consequences arising from
          platform use or unavailability.
        </p>
      </section>

      <section>
        <h2>9. FERPA Notice</h2>
        <p>
          For institutional deployments, Purplex operates as a "school official"
          with a legitimate educational interest under FERPA. Students have
          the right to inspect their educational records and request corrections.
          Contact your institution's registrar for FERPA-related requests.
        </p>
      </section>

      <section>
        <h2>10. Changes to Terms</h2>
        <p>
          We may update these terms with notice. Continued use after changes
          constitutes acceptance. Material changes may require re-consent.
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
    margin: 2rem auto;
    padding: 0 1.5rem 3rem;
}

.policy-page__content {
    color: var(--text-primary, #e0e0e0);
    line-height: 1.6;
}

.policy-page__version {
    color: var(--text-secondary, #999);
    font-size: 0.85rem;
    margin-bottom: 2rem;
}

.policy-page h1 {
    font-size: 1.8rem;
    margin-bottom: 0.25rem;
}

.policy-page h2 {
    font-size: 1.2rem;
    margin-top: 2rem;
    margin-bottom: 0.5rem;
}

.policy-page section {
    margin-bottom: 1rem;
}

.policy-page p,
.policy-page li {
    font-size: 0.9rem;
    color: var(--text-secondary, #ccc);
}

.policy-page ul {
    padding-left: 1.5rem;
}

.policy-page li {
    margin-bottom: 0.3rem;
}

.policy-page a {
    color: var(--link-color, #9b59b6);
}
</style>
