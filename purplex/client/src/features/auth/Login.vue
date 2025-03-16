<template>
  <div id="login-form">
    <form>

      <label for="email"><b>Email</b></label>
      <input v-model="email" type="text" placeholder="Enter your email" id="email" name="email" required />

      <label for="psw"><b>Password</b></label>
      <input v-model="password" type="password" placeholder="Enter your password" id="psw" name="psw" required />

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
  margin: 0 auto;
  width: 300px;
  padding: 20px;
  border: 2px solid #7d7d7d;
  border-radius: 5px;
}

form {
  display: flex;
  flex-direction: column;
}

label {
  margin-bottom: 10px;
}

input {
  padding: 10px;
  margin-bottom: 10px;
  border: 1px solid #7d7d7d;
  border-radius: 5px;
}

button {
  padding: 10px;
  border: none;
  border-radius: 5px;
  background-color: #333;
  color: #fff;
}

.login-btns {
  display: flex;
  justify-content: center;
}

.login-btns button {
  margin-left: 10px;
  margin-right: 10px;
}

.error-message {
  color: red;
  margin-top: 10px;
}
</style>
