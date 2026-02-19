import { nextTick, onBeforeUnmount, ref, type Ref, watch } from 'vue'

/**
 * Composable for managing focus trapping in modal dialogs.
 * Handles:
 * - Trapping Tab/Shift+Tab within modal
 * - Setting inert attribute on background content
 * - Saving and restoring focus when modal opens/closes
 *
 * @param isVisible - Reactive ref controlling modal visibility
 * @returns modalContentRef - Attach to modal content element via ref="modalContentRef"
 */
export function useFocusTrap(isVisible: Ref<boolean>, initialFocusRef?: Ref<HTMLElement | null>) {
  const modalContentRef = ref<HTMLElement | null>(null)
  const lastFocusedElement = ref<HTMLElement | null>(null)
  let focusTrapHandler: ((e: KeyboardEvent) => void) | null = null

  const candidateSelector =
    'button:not([disabled]):not([tabindex="-1"]), ' +
    '[href]:not([tabindex="-1"]), ' +
    'input:not([disabled]):not([tabindex="-1"]), ' +
    'select:not([disabled]):not([tabindex="-1"]), ' +
    'textarea:not([disabled]):not([tabindex="-1"]), ' +
    '[tabindex]:not([tabindex="-1"])'

  /**
   * Returns elements that can actually receive focus via Tab key.
   * Filters out elements inside inert/display:none/aria-hidden subtrees,
   * hidden elements, and Ace editor internals.
   */
  function getTabbableElements(container: HTMLElement): HTMLElement[] {
    return Array.from(container.querySelectorAll<HTMLElement>(candidateSelector)).filter(el => {
      // Must be visible (not in display:none ancestor, not hidden)
      if (el.offsetParent === null && getComputedStyle(el).position !== 'fixed') return false
      if (getComputedStyle(el).visibility === 'hidden') return false

      // Must not be inside an inert subtree
      if (el.closest('[inert]')) return false

      // Must not be an Ace editor internal element
      if (el.classList.contains('ace_text-input') || el.classList.contains('ace_content')) return false

      return true
    })
  }

  function activate(): void {
    lastFocusedElement.value = document.activeElement as HTMLElement
    setInert(true)
    nextTick(() => {
      trapFocus()
      focusFirstElement()
    })
  }

  function deactivate(): void {
    cleanup()
    setInert(false)
    lastFocusedElement.value?.focus()
  }

  function trapFocus(): void {
    const modal = modalContentRef.value
    if (!modal) {
      return
    }

    focusTrapHandler = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') {
        return
      }
      const focusable = getTabbableElements(modal)
      if (!focusable.length) {
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    modal.addEventListener('keydown', focusTrapHandler)
  }

  function focusFirstElement(): void {
    if (initialFocusRef?.value) {
      initialFocusRef.value.focus()
      return
    }
    const modal = modalContentRef.value
    if (!modal) {
      return
    }
    const tabbable = getTabbableElements(modal)
    tabbable[0]?.focus()
  }

  function setInert(inert: boolean): void {
    const appContent = document.getElementById('app-content')
    if (!appContent) {
      return
    }
    if (inert) {
      appContent.setAttribute('inert', '')
      appContent.setAttribute('aria-hidden', 'true')
    } else {
      appContent.removeAttribute('inert')
      appContent.removeAttribute('aria-hidden')
    }
  }

  function cleanup(): void {
    if (focusTrapHandler && modalContentRef.value) {
      modalContentRef.value.removeEventListener('keydown', focusTrapHandler)
      focusTrapHandler = null
    }
  }

  // Auto-activate/deactivate based on visibility
  watch(isVisible, (visible) => {
    if (visible) {
      activate()
    } else {
      deactivate()
    }
  })

  onBeforeUnmount(() => {
    cleanup()
    setInert(false)
  })

  return { modalContentRef }
}
