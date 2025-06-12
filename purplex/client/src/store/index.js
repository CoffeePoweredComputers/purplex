import { createStore } from "vuex";
import { auth } from "./auth.module";
import { courses } from "./courses.module";

const store = createStore({
  modules: {
    auth,
    courses,
  },
});

export default store;

