import { ActionContext, Module } from 'vuex';

export interface ConsentPromptState {
  visible: boolean;
  purpose: string | null;
}

type ConsentPromptActionContext = ActionContext<ConsentPromptState, unknown>;

// Promise plumbing kept out of Vuex state so the store stays serializable.
// A single decision promise is reused across concurrent requests — if two
// AI-gated calls land at the same time, we want ONE modal, not two.
let pendingResolver: ((granted: boolean) => void) | null = null;
let pendingPromise: Promise<boolean> | null = null;

export const consentPrompt: Module<ConsentPromptState, unknown> = {
  namespaced: true,

  state: (): ConsentPromptState => ({
    visible: false,
    purpose: null,
  }),

  mutations: {
    show(state: ConsentPromptState, purpose: string) {
      state.visible = true;
      state.purpose = purpose;
    },
    hide(state: ConsentPromptState) {
      state.visible = false;
      state.purpose = null;
    },
  },

  actions: {
    /**
     * Returns a promise that resolves when the user decides. If a prompt is
     * already visible for the same purpose, the existing promise is returned
     * so concurrent AI-gated requests share one decision.
     *
     * If a prompt is pending for a DIFFERENT purpose, the new call rejects
     * immediately rather than clobbering the in-flight resolver (which would
     * leave the original awaiters hanging forever). The store tracks a single
     * purpose at a time; supporting simultaneous distinct prompts is a scope
     * change that needs explicit design.
     */
    requestDecision(
      { commit, state }: ConsentPromptActionContext,
      purpose: string,
    ): Promise<boolean> {
      if (pendingPromise) {
        if (state.purpose === purpose) {
          return pendingPromise;
        }
        return Promise.reject(
          new Error(
            `consentPrompt: "${state.purpose}" is already pending; cannot start "${purpose}".`,
          ),
        );
      }

      pendingPromise = new Promise<boolean>((resolve) => {
        pendingResolver = resolve;
      });
      commit('show', purpose);
      return pendingPromise;
    },

    /**
     * Called by the modal UI when the user makes a choice.
     */
    resolveDecision({ commit }: ConsentPromptActionContext, granted: boolean) {
      if (pendingResolver) {
        pendingResolver(granted);
      }
      pendingResolver = null;
      pendingPromise = null;
      commit('hide');
    },
  },
};
