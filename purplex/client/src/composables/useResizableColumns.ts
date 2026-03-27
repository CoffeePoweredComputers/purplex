import { computed, type Ref, ref } from 'vue'

interface ResizableColumnsOptions {
  /** localStorage key for persisting column proportions */
  storageKey: string
  /** Initial column ratio, e.g. [1, 1] for equal or [2, 1] for 2:1 */
  initialRatios: [number, number]
  /** Width of the drag handle in px (grid column) */
  handleWidth?: number
  /** Minimum fraction each column can shrink to (0–1) */
  minFraction?: number
}

/**
 * Composable for resizable two-column grids.
 *
 * Returns a grid-template-columns string (e.g. "0.6fr 6px 0.4fr")
 * and pointer event handlers to bind on the drag handle element.
 * Uses setPointerCapture for clean drag tracking without global listeners.
 */
export function useResizableColumns(
  containerRef: Ref<HTMLElement | null>,
  options: ResizableColumnsOptions
) {
  const { storageKey, initialRatios, handleWidth = 6, minFraction = 0.15 } = options

  const total = initialRatios[0] + initialRatios[1]
  const defaultFraction = initialRatios[0] / total

  const stored = localStorage.getItem(storageKey)
  const leftFraction = ref(
    stored
      ? Math.max(minFraction, Math.min(1 - minFraction, parseFloat(stored)))
      : defaultFraction
  )

  const gridTemplate = computed(
    () => `${leftFraction.value}fr ${handleWidth}px ${1 - leftFraction.value}fr`
  )

  const isDragging = ref(false)
  let startX = 0
  let startFraction = 0

  function onPointerDown(e: PointerEvent) {
    if (!containerRef.value) {return}
    e.preventDefault()
    isDragging.value = true
    startX = e.clientX
    startFraction = leftFraction.value
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  function onPointerMove(e: PointerEvent) {
    if (!isDragging.value || !containerRef.value) {return}
    const containerWidth = containerRef.value.offsetWidth - handleWidth
    const delta = (e.clientX - startX) / containerWidth
    leftFraction.value = Math.max(
      minFraction,
      Math.min(1 - minFraction, startFraction + delta)
    )
  }

  function onPointerUp() {
    if (!isDragging.value) {return}
    isDragging.value = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    localStorage.setItem(storageKey, leftFraction.value.toFixed(4))
  }

  function reset() {
    leftFraction.value = defaultFraction
    localStorage.removeItem(storageKey)
  }

  return { gridTemplate, isDragging, onPointerDown, onPointerMove, onPointerUp, reset }
}
