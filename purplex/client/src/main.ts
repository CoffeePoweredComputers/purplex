import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import axios from "axios";

import router from "./router";
import store from "./store";

//import { FontAwesomeIcon } from './plugins/font-awesome'

axios.defaults.withCredentials = true
axios.defaults.baseURL = 'localhost:3000';

createApp(App)
    .use(router)
    .use(store)
    .mount('#app')
