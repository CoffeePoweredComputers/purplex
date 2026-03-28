<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div
        v-if="isVisible"
        class="modal-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby="modal-description"
        @click.self="closeModal"
      >
        <div
          ref="modalContentRef"
          class="modal-content"
          :style="modalStyle"
          @keydown.esc="closeModal"
        >
          <div class="modal-header">
            <h3
              id="modal-title"
              class="modal-title"
            >
              {{ $t('problems.pytutor.title') }}
            </h3>
            <span
              id="modal-description"
              class="sr-only"
            >{{ $t('problems.pytutor.srDescription') }}</span>
            <div class="modal-actions">
              <div class="size-controls-group">
                <span class="size-label">{{ $t('problems.pytutor.sizeLabel') }}</span>
                <div class="size-controls">
                  <button
                    v-for="size in sizePresets"
                    :key="size.name"
                    :class="['size-btn', { active: currentSize === size.name }]"
                    :title="$t('problems.pytutor.sizeView', { size: size.label })"
                    :aria-label="$t('problems.pytutor.setSizeAriaLabel', { size: size.label.toLowerCase() })"
                    @click="setModalSize(size.name)"
                  >
                    {{ size.icon }}
                  </button>
                </div>
              </div>
              <button
                class="action-button"
                :title="$t('problems.pytutor.openNewTab')"
                :aria-label="$t('problems.pytutor.openNewTabAriaLabel')"
                @click="openInNewTab"
              >
                <span class="icon">⬈</span>
              </button>
              <button
                class="close-button"
                :title="$t('problems.pytutor.closeEsc')"
                :aria-label="$t('problems.pytutor.closeModal')"
                @click="closeModal"
              >
                &times;
              </button>
            </div>
          </div>
          <div class="modal-body">
            <div
              v-if="loading"
              class="loading-container"
            >
              <div class="loading-spinner" />
              <p>{{ $t('problems.pytutor.loadingDebugger') }}</p>
            </div>
            <div
              v-show="!loading && !urlTooLong"
              v-if="pythonTutorUrl && !urlTooLong"
              class="iframe-wrapper"
            >
              <div class="iframe-header">
                <span class="iframe-info">{{ $t('problems.pytutor.pythonTutorVisualizer') }}</span>
                <button
                  class="theme-toggle"
                  :title="$t('problems.pytutor.switchTheme', { theme: isDarkWrapper ? 'light' : 'dark' })"
                  @click="toggleTheme"
                >
                  <span v-if="isDarkWrapper">🌞</span>
                  <span v-else>🌙</span>
                </button>
              </div>
              <iframe
                :src="pythonTutorUrl"
                :title="iframeTitle"
                width="100%"
                height="100%"
                tabindex="0"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                referrerpolicy="no-referrer"
                class="debugger-iframe"
                :class="{ 'dark-wrapper': isDarkWrapper }"
                @load="onIframeLoad"
                @error="onIframeError"
              />
            </div>
            <div
              v-if="urlTooLong"
              class="url-warning"
            >
              <p>{{ $t('problems.pytutor.codeTooLarge') }}</p>
              <p class="warning-details">
                {{ $t('problems.pytutor.urlLengthExceeded', { length: urlLength }) }}
              </p>
              <div class="warning-actions">
                <button
                  class="action-btn primary"
                  @click="copyAndOpen"
                >
                  <span>📋</span> {{ $t('problems.pytutor.copyCodeAndOpen') }}
                </button>
                <button
                  class="action-btn secondary"
                  @click="closeModal"
                >
                  {{ $t('common.cancel') }}
                </button>
              </div>
            </div>
            <div
              v-if="error"
              class="error-message"
            >
              <p class="error-icon">
                ❌
              </p>
              <h4 class="error-title">
                {{ getErrorTitle() }}
              </h4>
              <p class="error-description">
                {{ errorMessage }}
              </p>
              <div class="error-actions">
                <button
                  class="retry-button"
                  @click="retry"
                >
                  <span>🔄</span> {{ $t('common.tryAgain') }}
                </button>
                <a
                  v-if="errorType === 'TIMEOUT' || errorType === 'NETWORK'"
                  href="https://pythontutor.com"
                  target="_blank"
                  class="error-link"
                >
                  {{ $t('problems.pytutor.openDirectly') }}
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, toRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { log } from '@/utils/logger'
import { useFocusTrap } from '@/composables/useFocusTrap'

type SizePreset = 'small' | 'medium' | 'large' | 'fullscreen'
type ErrorType = 'TIMEOUT' | 'NETWORK' | null

interface SizePresetConfig {
  name: SizePreset
  label: string
  icon: string
  width: string
  height: string
}

const props = defineProps<{
  isVisible: boolean
  pythonTutorUrl: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'debugger-loaded'): void
  (e: 'debugger-error', payload: { type: ErrorType; message: string }): void
}>()

const { t } = useI18n()

// Focus trap composable
const { modalContentRef } = useFocusTrap(toRef(() => props.isVisible))

// Constants
const URL_LIMIT = 2000
const TIMEOUT_DURATION = 10000

// State
const loading = ref(true)
const error = ref(false)
const errorType = ref<ErrorType>(null)
const errorMessage = ref('')
const urlTooLong = ref(false)
const urlLength = ref(0)
const iframeTitle = ref(t('problems.pytutor.iframeTitle'))
const loadingTimeout = ref<ReturnType<typeof setTimeout> | null>(null)
const isDarkWrapper = ref(false)
const currentSize = ref<SizePreset>('medium')

const sizePresets = computed<SizePresetConfig[]>(() => [
  { name: 'small', label: t('problems.editor.size.small'), icon: '◻', width: '800px', height: '600px' },
  { name: 'medium', label: t('problems.editor.size.medium'), icon: '◼', width: '1200px', height: '800px' },
  { name: 'large', label: t('problems.editor.size.large'), icon: '⬛', width: '95%', height: '90vh' },
  { name: 'fullscreen', label: t('problems.editor.size.fullscreen'), icon: '⛶', width: '100%', height: '100vh' },
])

// Computed
const modalStyle = computed(() => {
  const preset = sizePresets.value.find(s => s.name === currentSize.value)
  if (!preset) {
    return {}
  }
  return {
    '--modal-width': preset.width,
    '--modal-height': preset.height,
    '--modal-max-width': preset.name === 'fullscreen' ? '100%' : preset.width,
    '--modal-max-height': preset.name === 'fullscreen' ? '100%' : preset.height,
  }
})

// Methods
function closeModal(): void {
  emit('close')
}

function checkUrlLength(): void {
  urlLength.value = props.pythonTutorUrl.length
  urlTooLong.value = urlLength.value > URL_LIMIT
  if (urlTooLong.value) {
    loading.value = false
  }
}

function startLoadingTimeout(): void {
  clearLoadingTimeout()
  loadingTimeout.value = setTimeout(() => {
    if (loading.value) {
      loading.value = false
      error.value = true
      errorType.value = 'TIMEOUT'
      errorMessage.value = t('problems.pytutor.timeoutMessage')
      emit('debugger-error', { type: errorType.value, message: errorMessage.value })
    }
  }, TIMEOUT_DURATION)
}

function clearLoadingTimeout(): void {
  if (loadingTimeout.value) {
    clearTimeout(loadingTimeout.value)
    loadingTimeout.value = null
  }
}

function onIframeLoad(): void {
  clearLoadingTimeout()
  loading.value = false
  error.value = false
  emit('debugger-loaded')
}

function onIframeError(): void {
  clearLoadingTimeout()
  loading.value = false
  error.value = true
  errorType.value = 'NETWORK'
  errorMessage.value = t('problems.pytutor.networkMessage')
  emit('debugger-error', { type: errorType.value, message: errorMessage.value })
}

function retry(): void {
  loading.value = true
  error.value = false
  errorType.value = null
  errorMessage.value = ''
  startLoadingTimeout()
  // Force iframe reload by setting src to itself
  const iframe = modalContentRef.value?.querySelector('.debugger-iframe') as HTMLIFrameElement | null
  if (iframe && iframe.src) {
    const currentSrc = iframe.src
    iframe.src = ''
    iframe.src = currentSrc
  }
}

function openInNewTab(): void {
  const regularUrl = props.pythonTutorUrl.replace('/iframe-embed.html', '/visualize.html')
  window.open(regularUrl, '_blank')
  closeModal()
}

function copyAndOpen(): void {
  const urlParams = new URL(props.pythonTutorUrl).hash.substring(1)
  const params = new URLSearchParams(urlParams)
  const code = params.get('code')

  if (code) {
    navigator.clipboard.writeText(code).then(() => {
      window.open('https://pythontutor.com/visualize.html#mode=edit', '_blank')
      closeModal()
    }).catch(err => {
      log.error('Failed to copy code', { error: err })
      window.open('https://pythontutor.com/visualize.html#mode=edit', '_blank')
    })
  }
}

function getErrorTitle(): string {
  switch (errorType.value) {
    case 'TIMEOUT':
      return t('problems.pytutor.loadingTimeout')
    case 'NETWORK':
      return t('problems.pytutor.connectionError')
    default:
      return t('problems.pytutor.failedToLoad')
  }
}

function toggleTheme(): void {
  isDarkWrapper.value = !isDarkWrapper.value
  localStorage.setItem('pytutor-dark-wrapper', String(isDarkWrapper.value))
}

function setModalSize(sizeName: SizePreset): void {
  currentSize.value = sizeName
  localStorage.setItem('pytutor-modal-size', sizeName)

  const modalContent = modalContentRef.value
  const modalOverlay = document.querySelector('.modal-overlay') as HTMLElement

  if (sizeName === 'fullscreen') {
    modalContent?.classList.add('fullscreen-mode')
    modalOverlay?.classList.add('fullscreen-overlay')
  } else {
    modalContent?.classList.remove('fullscreen-mode')
    modalOverlay?.classList.remove('fullscreen-overlay')
  }
}

// Watchers
watch(() => props.isVisible, (newVal) => {
  if (newVal) {
    loading.value = true
    error.value = false
    errorType.value = null
    errorMessage.value = ''
    checkUrlLength()

    if (!urlTooLong.value) {
      startLoadingTimeout()
    }
  } else {
    clearLoadingTimeout()
  }
})

watch(() => props.pythonTutorUrl, (newVal) => {
  if (newVal) {
    checkUrlLength()
  }
})

// Lifecycle
onMounted(() => {
  const savedTheme = localStorage.getItem('pytutor-dark-wrapper')
  if (savedTheme !== null) {
    isDarkWrapper.value = savedTheme === 'true'
  }
  const savedSize = localStorage.getItem('pytutor-modal-size') as SizePreset | null
  if (savedSize && sizePresets.value.find(s => s.name === savedSize)) {
    currentSize.value = savedSize
  }
})

onBeforeUnmount(() => {
  clearLoadingTimeout()
})
</script>

<style scoped>
/* Modal Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

/* Accessibility */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border-width: 0;
}

/* Modal Structure */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: var(--color-backdrop-heavy);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.modal-overlay.fullscreen-overlay {
  padding: 0;
}

.modal-content {
  background-color: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: var(--modal-width, 95%);
  height: var(--modal-height, 800px);
  max-width: var(--modal-max-width, 1400px);
  max-height: var(--modal-max-height, 90vh);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: var(--transition-base);
}

.modal-fade-enter-active .modal-content {
  transition: transform 0.3s ease;
}

.modal-fade-enter-from .modal-content {
  transform: scale(0.9);
}

.modal-content.fullscreen-mode {
  border-radius: 0;
  width: 100% !important;
  height: 100% !important;
  max-width: 100% !important;
  max-height: 100% !important;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--color-bg-header);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 2px solid var(--color-bg-input);
}

.modal-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.modal-actions {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
}

.size-controls-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  transition: var(--transition-fast);
}

.size-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: 500;
  user-select: none;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  opacity: 0.8;
}

.size-controls-group:hover .size-label {
  opacity: 1;
  color: var(--color-text-secondary);
}

.size-controls {
  display: flex;
  gap: var(--spacing-xs);
  background: var(--color-bg-dark);
  padding: var(--spacing-xs);
  border-radius: var(--radius-sm);
}

.size-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  width: 28px;
  height: 28px;
  border-radius: var(--radius-xs);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
  font-size: 14px;
  padding: 0;
}

.size-btn:hover {
  background: var(--color-bg-input);
  color: var(--color-text-secondary);
}

.size-btn.active {
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-xs);
}

.action-button {
  background: var(--color-bg-input);
  border: none;
  color: var(--color-text-secondary);
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
}

.action-button:hover {
  background: var(--color-primary);
  color: var(--color-text-on-filled);
  transform: translateY(-1px);
}

.icon {
  font-size: 18px;
}

.close-button {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: 24px;
  cursor: pointer;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
}

.close-button:hover {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.modal-body {
  flex: 1;
  position: relative;
  background: var(--color-bg-dark);
  overflow: hidden;
}

/* Loading State */
.loading-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 3px solid var(--color-bg-input);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-circle);
  animation: spin 1s linear infinite;
  margin: 0 auto var(--spacing-md);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  max-width: 400px;
  padding: var(--spacing-xl);
}

.error-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-md);
}

.error-title {
  color: var(--color-error);
  font-size: var(--font-size-md);
  margin-bottom: var(--spacing-sm);
}

.error-description {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
  line-height: 1.5;
}

.error-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}

.retry-button {
  background: var(--color-primary);
  color: var(--color-text-on-filled);
  border: none;
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 600;
  transition: var(--transition-fast);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.retry-button:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

.error-link {
  color: var(--color-primary);
  text-decoration: none;
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
}

.error-link:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}

/* Iframe Wrapper */
.iframe-wrapper {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-text-on-filled);
  overflow: hidden;
}

.iframe-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-panel);
  border-bottom: 1px solid var(--color-bg-border);
}

.iframe-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.theme-toggle {
  background: var(--color-bg-input);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
  font-size: 16px;
}

.theme-toggle:hover {
  background: var(--color-bg-hover);
  transform: scale(1.05);
}

/* Iframe */
.debugger-iframe {
  width: 100%;
  height: 100%;
  background: var(--color-text-on-filled);
  border: 0;
  transition: filter var(--transition-base);
}

.debugger-iframe.dark-wrapper {
  filter: invert(0.88) hue-rotate(180deg);
  background: var(--color-bg-dark);
}

/* URL Warning */
.url-warning {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-base);
  max-width: 500px;
}

.url-warning p {
  color: var(--color-warning);
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-md);
}

.warning-details {
  color: var(--color-text-secondary) !important;
  font-size: var(--font-size-sm) !important;
}

.warning-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: center;
  margin-top: var(--spacing-lg);
}

.action-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: 600;
  transition: var(--transition-fast);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.action-btn.primary {
  background: var(--color-primary);
  color: var(--color-text-on-filled);
}

.action-btn.primary:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: var(--color-bg-input);
  color: var(--color-text-secondary);
  border-color: var(--color-bg-border);
}

.action-btn.secondary:hover {
  background: var(--color-bg-hover);
}

/* Responsive */
@media (width <= 768px) {
  .modal-overlay {
    padding: 0;
  }

  .modal-content {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
    border-radius: 0;
  }

  .modal-header {
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .modal-title {
    font-size: var(--font-size-base);
  }

  .size-controls-group {
    display: none; /* Hide size controls on mobile */
  }

  .modal-actions {
    gap: var(--spacing-sm);
  }
}
</style>
