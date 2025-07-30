import { FirebaseApp, initializeApp } from "firebase/app";
import { Auth, getAuth } from "firebase/auth";

// Firebase configuration object
interface FirebaseConfig {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket: string;
  messagingSenderId: string;
  appId: string;
}

const firebaseConfig: FirebaseConfig = {
  apiKey: "AIzaSyCsyYati6ns2CCWgxIuHlHly_VOhXD2sS4",
  authDomain: "purplex-97ff2.firebaseapp.com",
  projectId: "purplex-97ff2",
  storageBucket: "purplex-97ff2.appspot.com",
  messagingSenderId: "863513714403",
  appId: "1:863513714403:web:7207f4a20890ca236d2fd6"
};

const firebaseApp: FirebaseApp = initializeApp(firebaseConfig);
const firebaseAuth: Auth = getAuth();

export { firebaseApp, firebaseAuth };