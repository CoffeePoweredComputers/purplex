import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

const firebaseConfig = {
  apiKey: "AIzaSyCsyYati6ns2CCWgxIuHlHly_VOhXD2sS4",
  authDomain: "purplex-97ff2.firebaseapp.com",
  projectId: "purplex-97ff2",
  storageBucket: "purplex-97ff2.appspot.com",
  messagingSenderId: "863513714403",
  appId: "1:863513714403:web:7207f4a20890ca236d2fd6"
};

const firebaseApp = initializeApp(firebaseConfig);

const firebaseAuth = getAuth();

export { firebaseApp, firebaseAuth };