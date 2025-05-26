<template>
  <div id="login-form">
    <form>

      <div class="form-field">
        <label for="email" class="field-label">
          <span class="label-text">Email Address</span>
          <span class="label-subtitle">Use your work or personal email</span>
        </label>
        <input v-model="email" type="email" placeholder="you@example.com" id="email" name="email" required />
      </div>

      <div class="form-field">
        <label for="psw" class="field-label">
          <span class="label-text">Password</span>
          <span class="label-subtitle">Must be at least 6 characters</span>
        </label>
        <input v-model="password" type="password" placeholder="Enter your password" id="psw" name="psw" required />
      </div>

      <div class="login-btns">
        <button type="button" @click="login">Login</button>
        <button type="button" @click="createAccount">New Account</button>
        <button type="button" @click="loginWithGoogle">Login with Google</button>
      </div>

      <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>

    </form>
  </div>
</template>

<script lang="ts">
import { GoogleAuthProvider } from 'firebase/auth/web-extension';


export default {
  name: "Login",
  data() {
    return {
      email: '',
      password: '',
      errorMessage: ''
    };
  },
  methods: {
      login: async function () {
        const { email, password } = this;
        this.$store.dispatch('auth/login', { email, password })
          .then(() => {
            this.$router.push({ name: "Home" });
          })
          .catch((error) => {
            const message = this.mapFirebaseErrorToMessage(error);
            this.displayErrorMessage(message); 
          });
      },
      loginWithGoogle: async function () {
        const provider = new GoogleAuthProvider();
        this.$store.dispatch('auth/loginWithGoogle', provider)
          .then(() => {
            this.$router.push({ name: "Home" });
          })
          .catch((error) => {
            const message = this.mapFirebaseErrorToMessage(error);
            this.displayErrorMessage(message); 
          });
      },
      createAccount: async function () {
        const { email, password } = this;
        this.$store.dispatch('auth/createAccount', { email, password })
          .then(() => {
            this.$router.push({ name: "Home" });
          })
          .catch((error) => {
            const message = this.mapFirebaseErrorToMessage(error);
            this.displayErrorMessage(message); 
          });
      },
      mapFirebaseErrorToMessage: function (error) {

        /* We don't want the use just closing the account popup to be reported as an error */
        /* TODO: I cant remember why this is needed... look into it later */
        if (error.code === "auth/popup-closed-by-user") {
          return;
        }

        const errorMessages = {
          'auth/email-already-in-use': 'This email is already in use. Please try another one.',
          'auth/weak-password': 'The password is too weak. Please use a stronger password.',
          'auth/internal-error': 'An internal error occurred. Please try again later.',
          'auth/invalid-credential': 'Your password is invalid.',
          'auth/too-many-requests': 'Too many requests to login. Please try again later.',
          'auth/missing-fields': 'Please enter an email and password.',
          'auth/no-google-auth-in-debug': 'Google authentication is not available in debug mode.',
          'auth/registration-failed': 'Registration failed. Unable to register the new user.',
        };


        if (errorMessages[error.code]) {
          return errorMessages[error.code];
        } else if (error.message) { // a ditch attempt to get a message
          return error.message;
        } else {
          return 'An unknown error occurred. Please try again later.';
        }
      },
      displayErrorMessage: function (message) {
        this.errorMessage = message; 
      }
  }
};

</script>

<style scoped>
#login-form {
  margin: 60px auto;
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
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
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
  color: var(--color-text-primary);
  box-shadow: var(--shadow-colored);
}

.login-btns button:first-child:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
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

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

/* Responsive Design */
@media (max-width: 768px) {
  #login-form {
    margin: 20px;
    padding: var(--spacing-xl);
  }
  
  .login-btns button {
    font-size: var(--font-size-sm);
  }
}
</style>
