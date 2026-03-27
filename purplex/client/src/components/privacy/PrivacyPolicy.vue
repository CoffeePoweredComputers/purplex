<template>
  <!-- eslint-disable vue/no-v-html -- Content from vue-i18n translations (trusted source) -->
  <div class="policy-page">
    <div class="policy-page__content">
      <h1>{{ t('auth.privacyPage.title') }}</h1>
      <p class="policy-page__version">
        {{ t('auth.privacyPage.version', { effectiveDate }) }}
      </p>

      <section>
        <h2>{{ t('auth.privacyPage.section1.title') }}</h2>
        <p v-html="t('auth.privacyPage.section1.content')" />
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section2.title') }}</h2>
        <ul>
          <li v-html="t('auth.privacyPage.section2.items.identityData')" />
          <li v-html="t('auth.privacyPage.section2.items.submissionData')" />
          <li v-html="t('auth.privacyPage.section2.items.progressData')" />
          <li v-html="t('auth.privacyPage.section2.items.aiAnalysisData')" />
          <li v-html="t('auth.privacyPage.section2.items.technicalData')" />
        </ul>
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section3.title') }}</h2>
        <ul>
          <li>{{ t('auth.privacyPage.section3.items.providePlatform') }}</li>
          <li>{{ t('auth.privacyPage.section3.items.trackProgress') }}</li>
          <li>{{ t('auth.privacyPage.section3.items.aiAnalysis') }}</li>
          <li>{{ t('auth.privacyPage.section3.items.improvePlatform') }}</li>
        </ul>
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section4.title') }}</h2>
        <p>{{ t('auth.privacyPage.section4.intro') }}</p>
        <ul>
          <li v-html="t('auth.privacyPage.section4.items.firebase')" />
          <li v-html="t('auth.privacyPage.section4.items.openai')" />
        </ul>
        <p>{{ t('auth.privacyPage.section4.transfers') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section5.title') }}</h2>
        <p>{{ t('auth.privacyPage.section5.intro') }}</p>
        <ul>
          <li v-html="t('auth.privacyPage.section5.items.access')" />
          <li v-html="t('auth.privacyPage.section5.items.rectification')" />
          <li v-html="t('auth.privacyPage.section5.items.erasure')" />
          <li v-html="t('auth.privacyPage.section5.items.portability')" />
          <li v-html="t('auth.privacyPage.section5.items.object')" />
          <li v-html="t('auth.privacyPage.section5.items.restrictProcessing')" />
        </ul>
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section6.title') }}</h2>
        <ul>
          <li>{{ t('auth.privacyPage.section6.items.submissions') }}</li>
          <li>{{ t('auth.privacyPage.section6.items.progressSnapshots') }}</li>
          <li>{{ t('auth.privacyPage.section6.items.serverLogs') }}</li>
          <li>{{ t('auth.privacyPage.section6.items.inactiveAccounts') }}</li>
        </ul>
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section7.title') }}</h2>
        <p>{{ t('auth.privacyPage.section7.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section8.title') }}</h2>
        <p>{{ t('auth.privacyPage.section8.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section9.title') }}</h2>
        <p>{{ t('auth.privacyPage.section9.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section10.title') }}</h2>
        <p>{{ t('auth.privacyPage.section10.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.privacyPage.section11.title') }}</h2>
        <p>{{ t('auth.privacyPage.section11.content') }}</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

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
