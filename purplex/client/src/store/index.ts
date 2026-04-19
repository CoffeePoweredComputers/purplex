import { createStore, Store } from "vuex";
import { auth, AuthState } from "./auth.module";
import { consentPrompt, ConsentPromptState } from "./consentPrompt.module";
import { courses, CoursesState } from "./courses.module";

export interface RootState {
  auth: AuthState;
  courses: CoursesState;
  consentPrompt: ConsentPromptState;
}

const store: Store<RootState> = createStore({
  modules: {
    auth,
    courses,
    consentPrompt,
  },
});

export default store;
