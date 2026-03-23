<template>
  <div class="login-page">
    <div class="login-header">
      <div class="title-with-logo">
        <img
          src="/plx-logo.png"
          alt="Purplex Logo"
          class="login-logo"
        >
        <h1 class="login-title">
          {{ $t('brand.name') }}
        </h1>
      </div>
      <p class="login-subtitle">
        {{ $t('brand.tagline') }}
      </p>
    </div>

    <!-- Step 1: Credentials (login or start registration) -->
    <div v-if="registrationStep === 'credentials'" id="login-form">
      <form>
        <div class="form-field">
          <label
            for="email"
            class="field-label"
          >
            <span class="label-text">{{ $t('auth.login.email.label') }}</span>
            <span class="label-subtitle">{{ $t('auth.login.email.hint') }}</span>
          </label>
          <input
            id="email"
            v-model="email"
            type="email"
            :placeholder="$t('auth.login.email.placeholder')"
            name="email"
            required
          >
        </div>

        <div class="form-field">
          <label
            for="psw"
            class="field-label"
          >
            <span class="label-text">{{ $t('auth.login.password.label') }}</span>
            <span class="label-subtitle">{{ $t('auth.login.password.hint') }}</span>
          </label>
          <input
            id="psw"
            v-model="password"
            type="password"
            :placeholder="$t('auth.login.password.placeholder')"
            name="psw"
            required
          >
        </div>

        <div class="login-btns">
          <button
            type="button"
            :disabled="isLoading"
            @click="login"
          >
            <span v-if="isLoading">{{ $t('auth.login.submitLoading') }}</span>
            <span v-else>{{ $t('auth.login.submit') }}</span>
          </button>
          <button
            type="button"
            :disabled="isLoading"
            @click="startRegistration"
          >
            {{ $t('auth.login.createAccount') }}
          </button>
          <button
            type="button"
            :disabled="isLoading"
            @click="loginWithGoogle"
          >
            <span v-if="isLoading">{{ $t('auth.login.googleLoading') }}</span>
            <span v-else>{{ $t('auth.login.google') }}</span>
          </button>
          <button
            v-if="showRedirectOption"
            type="button"
            :disabled="isLoading"
            class="redirect-mode-btn"
            @click="loginWithGoogleRedirect"
          >
            {{ $t('auth.login.redirectMode') }}
          </button>
        </div>

        <div
          v-if="errorMessage"
          class="error-message"
        >
          {{ errorMessage }}
        </div>

        <div
          v-if="showRedirectOption"
          class="info-message"
        >
          {{ $t('auth.login.redirectHint') }}
        </div>
      </form>

      <div class="login-footer-links">
        <router-link to="/privacy">{{ $t('auth.login.privacyPolicy') }}</router-link>
        <span class="link-separator">|</span>
        <router-link to="/terms">{{ $t('auth.login.termsOfService') }}</router-link>
      </div>
    </div>

    <!-- Step 2: Age Verification (registration flow) -->
    <div v-else-if="registrationStep === 'age-gate'" class="registration-step">
      <button class="back-btn" @click="registrationStep = 'credentials'">{{ $t('common.back') }}</button>
      <AgeGate
        @age-verified="onAgeVerified"
        @under-age="onUnderAge"
      />
    </div>

    <!-- Step 3: Consent Form (registration flow) -->
    <div v-else-if="registrationStep === 'consent'" class="registration-step">
      <button class="back-btn" @click="registrationStep = 'age-gate'">{{ $t('common.back') }}</button>
      <ConsentForm @consent-granted="onConsentGranted" />
      <div
        v-if="errorMessage"
        class="error-message registration-error"
      >
        {{ errorMessage }}
      </div>
    </div>

    <!-- Under-age block (COPPA) -->
    <div v-else-if="registrationStep === 'under-age'" class="registration-step">
      <div class="under-age-notice">
        <h3>{{ $t('auth.coppa.title') }}</h3>
        <p>{{ $t('auth.coppa.message') }}</p>
        <button class="back-btn" @click="registrationStep = 'credentials'">{{ $t('auth.coppa.backToLogin') }}</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { GoogleAuthProvider } from 'firebase/auth';
import ConsentForm from '../../components/privacy/ConsentForm.vue';
import AgeGate from '../../components/privacy/AgeGate.vue';
import privacyService, { type ConsentType } from '../../services/privacyService';


export default {
  name: "Login",
  components: {
    ConsentForm,
    AgeGate,
  },
  data() {
    return {
      email: '',
      password: '',
      errorMessage: '',
      isLoading: false,
      showRedirectOption: false,
      // Registration flow state
      registrationStep: 'credentials' as 'credentials' | 'age-gate' | 'consent' | 'under-age',
      ageData: null as { date_of_birth: string; is_minor: boolean; is_child: boolean } | null,
    };
  },
  methods: {
      login: async function () {
        const { email, password } = this;
        this.isLoading = true;
        this.errorMessage = '';

        this.$store.dispatch('auth/login', { email, password })
          .then(() => {
            this.$router.push({ name: "Home" });
          })
          .catch((error) => {
            const message = this.mapFirebaseErrorToMessage(error);
            this.displayErrorMessage(message);
          })
          .finally(() => {
            this.isLoading = false;
          });
      },
      loginWithGoogle: async function (useRedirect = false) {
        this.isLoading = true;
        this.errorMessage = '';

        this.$store.dispatch('auth/loginWithGoogle', { useRedirect })
          .then(() => {
            this.$router.push({ name: "Home" });
          })
          .catch((error) => {
            // Check if error suggests using redirect mode
            if (error.shouldUseRedirect) {
              this.showRedirectOption = true;
              const message = this.mapFirebaseErrorToMessage(error);
              this.displayErrorMessage(message);
            } else {
              const message = this.mapFirebaseErrorToMessage(error);
              this.displayErrorMessage(message);
            }
          })
          .finally(() => {
            this.isLoading = false;
          });
      },
      loginWithGoogleRedirect: async function () {
        // Explicitly use redirect mode
        this.isLoading = true;
        this.errorMessage = '';
        await this.loginWithGoogle(true);
      },
      // Step 1: Validate credentials before entering consent flow
      startRegistration: function () {
        if (!this.email || !this.password) {
          this.displayErrorMessage(this.$t('auth.errors.missingFields'));
          return;
        }
        if (this.password.length < 6) {
          this.displayErrorMessage(this.$t('auth.login.password.tooShort'));
          return;
        }
        this.errorMessage = '';
        this.registrationStep = 'age-gate';
      },
      // Step 2: Age verification completed
      onAgeVerified: function (data: { date_of_birth: string; is_minor: boolean; is_child: boolean }) {
        this.ageData = data;
        this.registrationStep = 'consent';
      },
      onUnderAge: function () {
        this.registrationStep = 'under-age';
      },
      // Step 3: Consent granted — now create the account
      onConsentGranted: async function (consents: Record<string, boolean>) {
        this.isLoading = true;
        this.errorMessage = '';

        try {
          // Create the Firebase account
          const { email, password } = this;
          await this.$store.dispatch('auth/createAccount', { email, password });

          // Submit age verification
          if (this.ageData) {
            try {
              await privacyService.submitAgeVerification({
                date_of_birth: this.ageData.date_of_birth,
                is_minor: this.ageData.is_minor,
                is_child: this.ageData.is_child,
              });
            } catch {
              // Age verification submission failed — non-blocking
            }
          }

          // Submit each granted consent to the backend
          const consentTypes = Object.entries(consents)
            .filter(([, granted]) => granted)
            .map(([type]) => type as ConsentType);

          for (const consentType of consentTypes) {
            try {
              await privacyService.grantConsent(consentType);
            } catch {
              // Individual consent grant failed — non-blocking
            }
          }

          // Registration complete — navigate to Home
          this.$router.push({ name: "Home" });
        } catch (error) {
          const message = this.mapFirebaseErrorToMessage(error);
          this.displayErrorMessage(message);
        } finally {
          this.isLoading = false;
        }
      },
      mapFirebaseErrorToMessage: function (error) {

        /* Silently ignore popup-closed — the user dismissing the popup is not an error */
        if (error.code === "auth/popup-closed-by-user") {
          return;
        }

        const errorKeyMap: Record<string, string> = {
          'auth/email-already-in-use': 'auth.errors.emailInUse',
          'auth/weak-password': 'auth.errors.weakPassword', // pragma: allowlist secret
          'auth/internal-error': 'auth.errors.internalError',
          'auth/invalid-credential': 'auth.errors.invalidCredential',
          'auth/too-many-requests': 'auth.errors.tooManyRequests',
          'auth/missing-fields': 'auth.errors.missingFields',
          'auth/no-google-auth-in-debug': 'auth.errors.noGoogleAuthDebug',
          'auth/registration-failed': 'auth.errors.registrationFailed',
          'auth/cookies-blocked': 'auth.errors.cookiesBlocked',
          'auth/popup-timeout-redirect': 'auth.errors.popupTimeout',
          'auth/popup-blocked': 'auth.errors.popupBlocked',
          'auth/network-error': 'auth.errors.networkError',
          'auth/google-login-failed': 'auth.errors.googleLoginFailed',
          'auth/redirect-failed': 'auth.errors.redirectFailed',
        };

        const key = errorKeyMap[error.code];
        if (key) {
          return this.$t(key);
        } else if (error.message) { // a ditch attempt to get a message
          return error.message;
        } else {
          return this.$t('auth.errors.unknown');
        }
      },
      displayErrorMessage: function (message) {
        this.errorMessage = message;
      }
  }
};

</script>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--spacing-xl);
  padding-bottom: calc(var(--spacing-xxl) * 5);
}

.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-xxl);
  text-align: center;
}

.title-with-logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-xxl);
}

.login-logo {
  width: 80px;
  height: 80px;
  margin: var(--spacing-lg);
  object-fit: cover;
  object-position: center center;
  transform: scale(3.8);
}

.login-title {
  font-family: 'Exo 2', sans-serif;
  font-size: var(--font-size-title);
  margin: 0;
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 50%, var(--color-admin-hover) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 800;
  letter-spacing: 1px;
}

.login-subtitle {
  font-size: var(--font-size-lg);
  color: var(--color-text-muted);
  margin: 0;
  max-width: 500px;
}

#login-form {
  width: 100%;
  max-width: 400px;
  padding: calc(var(--spacing-xl) + 10px) calc(var(--spacing-xxl) + 10px);
  background: var(--color-bg-panel);
  border-radius: calc(var(--radius-lg) + 4px);
  box-shadow: var(--shadow-base);
  border: 2px solid transparent;
  transition: var(--transition-base);
}

#login-form:hover {
  border-color: var(--color-bg-input);
  box-shadow: var(--shadow-lg);
}


form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.field-label {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-xs);
}

.label-text {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.label-subtitle {
  font-size: var(--font-size-sm);
  font-weight: 400;
  color: var(--color-text-muted);
  letter-spacing: -0.005em;
}

input {
  width: 100%;
  padding: calc(var(--spacing-md) + 2px) var(--spacing-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-fast);
}

input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px var(--color-primary-overlay);
}

input::placeholder {
  color: var(--color-text-muted);
}

.login-btns {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
}

.login-btns button {
  padding: var(--spacing-md) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-base);
  cursor: pointer;
  transition: var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.login-btns button:first-child {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-on-filled);
  box-shadow: var(--shadow-colored);
}

.login-btns button:first-child:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--color-primary-glow);
}


.login-btns button:nth-child(2) {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.login-btns button:nth-child(2):hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.login-btns button:nth-child(2)::before {
  content: "✨";
}

.login-btns button:nth-child(3) {
  background: var(--color-bg-main);
  color: var(--color-text-primary);
  border: 2px solid var(--color-bg-border);
  position: relative;
  overflow: hidden;
}

.login-btns button:nth-child(3):hover {
  border-color: var(--color-primary-gradient-start);
  transform: translateY(-1px);
}

.login-btns button:nth-child(3)::before {
  content: "🌐";
}

.login-btns button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.login-btns button:disabled:hover {
  transform: none !important;
  box-shadow: var(--shadow-base) !important;
}

.redirect-mode-btn {
  background: var(--color-bg-hover) !important;
  color: var(--color-text-secondary) !important;
  border: 1px dashed var(--color-bg-border) !important;
  font-size: var(--font-size-sm) !important;
}

.redirect-mode-btn::before {
  content: "🔄";
}

.redirect-mode-btn:hover {
  background: var(--color-bg-input) !important;
  border-color: var(--color-primary-gradient-start) !important;
  color: var(--color-text-primary) !important;
}

.error-message {
  background: var(--color-error-bg);
  color: var(--color-error);
  padding: var(--spacing-md);
  border-radius: var(--radius-base);
  text-align: center;
  font-size: var(--font-size-sm);
  border: 1px solid var(--color-error);
  animation: shake 0.5s ease-in-out;
}

.info-message {
  background: var(--color-primary-overlay);
  color: var(--color-text-secondary);
  padding: var(--spacing-md);
  border-radius: var(--radius-base);
  text-align: center;
  font-size: var(--font-size-sm);
  border: 1px solid var(--color-primary-glow);
  line-height: 1.5;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

/* Registration step containers */
.registration-step {
  width: 100%;
  max-width: 500px;
}

.back-btn {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: var(--font-size-sm);
  padding: var(--spacing-sm) 0;
  margin-bottom: var(--spacing-md);
  transition: color 0.2s;
}

.back-btn:hover {
  color: var(--color-text-primary);
}

.back-btn::before {
  content: "\2190 ";
}

.registration-error {
  margin-top: var(--spacing-md);
}

.under-age-notice {
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-warning-overlay);
  text-align: center;
}

.under-age-notice h3 {
  color: var(--color-warning);
  margin: 0 0 var(--spacing-md);
  font-size: var(--font-size-lg);
}

.under-age-notice p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  margin: 0 0 var(--spacing-lg);
}

.login-footer-links {
  display: flex;
  justify-content: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-lg);
  font-size: var(--font-size-sm);
}

.login-footer-links a {
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color 0.2s;
}

.login-footer-links a:hover {
  color: var(--color-text-secondary);
}

.link-separator {
  color: var(--color-text-muted);
  opacity: 0.5;
}

/* Responsive Design */
@media (max-width: 768px) {
  .login-title {
    font-size: calc(var(--font-size-title) * 0.75);
  }

  .login-subtitle {
    font-size: var(--font-size-base);
  }

  .login-logo {
    width: 80px;
    height: 80px;
  }

  #login-form {
    padding: var(--spacing-xl);
  }

  .login-btns button {
    font-size: var(--font-size-sm);
  }
}

@media (max-width: 480px) {
  .login-title {
    font-size: calc(var(--font-size-title) * 0.6);
  }

  .login-header {
    margin-bottom: var(--spacing-xl);
  }
}
</style>
