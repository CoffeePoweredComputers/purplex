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
export function useFocusTrap(isVisible: Ref<boolean>) {
  const modalContentRef = ref<HTMLElement | null>(null)
  const lastFocusedElement = ref<HTMLElement | null>(null)
  let focusTrapHandler: ((e: KeyboardEvent) => void) | null = null

  const focusableSelector =
    'button, [href], input, select, textarea, iframe[tabindex], [tabindex]:not([tabindex="-1"])'

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
      const focusable = modal.querySelectorAll<HTMLElement>(focusableSelector)
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
    const modal = modalContentRef.value
    if (!modal) {
      return
    }
    const first = modal.querySelector(focusableSelector) as HTMLElement
    first?.focus()
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
