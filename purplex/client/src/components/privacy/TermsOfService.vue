<template>
  <div class="policy-page">
    <div class="policy-page__content">
      <h1>{{ t('auth.termsPage.title') }}</h1>
      <p class="policy-page__version">
        {{ t('auth.termsPage.version', { effectiveDate }) }}
      </p>

      <section>
        <h2>{{ t('auth.termsPage.section1.title') }}</h2>
        <p v-html="t('auth.termsPage.section1.content', { privacyPolicyLink: `<a href=&quot;/privacy&quot;>${t('auth.privacyPage.title')}</a>` })" />
      </section>

      <section>
        <h2>{{ t('auth.termsPage.section2.title') }}</h2>
        <p>{{ t('auth.termsPage.section2.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.termsPage.section3.title') }}</h2>
        <p>{{ t('auth.termsPage.section3.intro') }}</p>
        <ul>
          <li>{{ t('auth.termsPage.section3.items.codeVariations') }}</li>
          <li>{{ t('auth.termsPage.section3.items.comprehensionAnalysis') }}</li>
          <li>{{ t('auth.termsPage.section3.items.educationalFeedback') }}</li>
        </ul>
        <p>{{ t('auth.termsPage.section3.optOut') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.termsPage.section4.title') }}</h2>
        <p>{{ t('auth.termsPage.section4.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.termsPage.section5.title') }}</h2>
        <p>{{ t('auth.termsPage.section5.intro') }}</p>
        <ul>
          <li>{{ t('auth.termsPage.section5.items.maliciousCode') }}</li>
          <li>{{ t('auth.termsPage.section5.items.accessOthersData') }}</li>
          <li>{{ t('auth.termsPage.section5.items.unrelatedUse') }}</li>
          <li>{{ t('auth.termsPage.section5.items.shareCredentials') }}</li>
        </ul>
      </section>

      <section>
        <h2>{{ t('auth.termsPage.section6.title') }}</h2>
        <p>{{ t('auth.termsPage.section6.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.termsPage.section7.title') }}</h2>
        <p>{{ t('auth.termsPage.section7.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.termsPage.section8.title') }}</h2>
        <p>{{ t('auth.termsPage.section8.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.termsPage.section9.title') }}</h2>
        <p>{{ t('auth.termsPage.section9.content') }}</p>
      </section>

      <section>
        <h2>{{ t('auth.termsPage.section10.title') }}</h2>
        <p>{{ t('auth.termsPage.section10.content') }}</p>
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
