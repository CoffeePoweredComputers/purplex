import { createStore, Store } from "vuex";
import { auth, AuthState } from "./auth.module";
import { courses, CoursesState } from "./courses.module";

export interface RootState {
  auth: AuthState;
  courses: CoursesState;
}

const store: Store<RootState> = createStore({
  modules: {
    auth,
    courses,
  },
});

export default store;
