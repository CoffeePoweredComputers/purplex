<template>
  <div class="segment-mapping">
    <div class="sr-only" aria-live="polite" aria-atomic="true">
      {{ segmentAnnouncement }}
    </div>
    <div class="mapping-grid-simplified">
      <!-- Left: Student Response with Inline Segments -->
      <div class="response-panel" role="region" aria-label="Your explanation">
        <h4 class="panel-title">
          <span class="title-icon" aria-hidden="true">💭</span>
          {{ $t('feedback.segmentMapping.yourExplanation') }}
        </h4>
        <div class="response-text">
          <span
            v-for="(part, index) in parsedResponse"
            :key="`part-${index}`"
            :class="{
              'segment-span': part.isSegment,
              'active': part.isSegment && activeSegment === part.segmentId
            }"
            v-bind="part.isSegment ? {
              tabindex: 0,
              role: 'button',
              'aria-pressed': activeSegment === part.segmentId,
              'aria-label': `Segment ${getSegmentNumber(part.segmentId!)}: ${part.text}`
            } : {}"
            @mouseenter="part.isSegment && setActiveSegment(part.segmentId!)"
            @mouseleave="part.isSegment && clearActiveSegment()"
            @focus="part.isSegment && setActiveSegment(part.segmentId!)"
            @blur="part.isSegment && clearActiveSegment()"
            @keydown.enter="part.isSegment && toggleSegment(part.segmentId!)"
            @keydown.space.prevent="part.isSegment && toggleSegment(part.segmentId!)"
          >
            <template v-if="part.isSegment">
              <span
                class="segment-marker"
                :style="{
                  borderColor: getSegmentColor(part.segmentId),
                  color: getSegmentColor(part.segmentId),
                  '--segment-bg-color': getSegmentColor(part.segmentId)
                }"
              >
                {{ getSegmentNumber(part.segmentId) }}
              </span>
              <span
                class="segment-text"
                :style="{
                  color: getSegmentColor(part.segmentId),
                  borderBottomColor: getSegmentColor(part.segmentId)
                }"
              >{{ part.text }}</span>
            </template>
            <template v-else>{{ part.text }}</template>
          </span>
        </div>
      </div>

      <!-- Right: Code with Highlights -->
      <div class="code-panel" role="region" aria-label="Reference code">
        <h4 class="panel-title">
          <span class="title-icon" aria-hidden="true">📝</span>
          {{ $t('feedback.segmentMapping.referenceCode') }}
        </h4>
        <div class="code-display">
          <div
            v-for="(line, index) in codeLines"
            :key="index"
            class="code-line"
            :class="getLineClass(index + 1)"
            :aria-current="isLineHighlighted(index + 1) ? 'true' : undefined"
          >
            <span
              class="line-number"
              :style="getLineSegmentId(index + 1) ? {
                borderLeftColor: getSegmentColor(getLineSegmentId(index + 1)),
                borderLeftWidth: activeSegment === getLineSegmentId(index + 1) ? '6px' : '3px'
              } : {}"
              :data-segment-id="getLineSegmentId(index + 1)"
            >
              {{ index + 1 }}
            </span>
            <code class="line-content"><span
                v-for="(token, tIdx) in tokenizedLines[index]"
                :key="tIdx"
                :class="tokenClass(token.type)"
              >{{ token.value }}</span></code>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue';
import { tokenizePython, type TokenizedLine } from '@/utils/pythonTokenizer';

// Define types for the component
interface Segment {
  id: number;
  text: string;
  code_lines: number[];
}

interface ParsedResponsePart {
  text: string;
  isSegment: boolean;
  segmentId?: number;
}

export default defineComponent({
  name: 'SegmentMapping',
  props: {
    segments: {
      type: Array as PropType<Segment[]>,
      required: true,
      default: (): Segment[] => []
    },
    referenceCode: {
      type: String,
      required: true,
      default: ''
    },
    userPrompt: {
      type: String,
      required: true,
      default: ''
    }
  },
  data() {
    return {
      activeSegment: null as number | null,
      selectedSegment: null as number | null,
      canvasWidth: 200 as number,
      canvasHeight: 400 as number,
      connectionColor: '#667eea' as string
    };
  },
  computed: {
    codeLines(): string[] {
      // Don't filter out empty lines to maintain line numbering
      return this.referenceCode.split('\n');
    },

    tokenizedLines(): TokenizedLine[] {
      return tokenizePython(this.referenceCode);
    },

    segmentAnnouncement(): string {
      if (!this.activeSegment) {
        return '';
      }
      const segment = this.segments.find(s => s.id === this.activeSegment);
      if (!segment || !segment.code_lines || segment.code_lines.length === 0) {
        return '';
      }
      const num = this.getSegmentNumber(this.activeSegment);
      const lines = segment.code_lines;
      const min = Math.min(...lines);
      const max = Math.max(...lines);
      return min === max
        ? `Segment ${num} highlighted, covering line ${min}`
        : `Segment ${num} highlighted, covering lines ${min} to ${max}`;
    },

    parsedResponse(): ParsedResponsePart[] {

      if (!this.userPrompt) {
        return [{ text: '', isSegment: false }];
      }

      if (!this.segments || this.segments.length === 0) {
        return [{ text: this.userPrompt, isSegment: false }];
      }

      // Try to reconstruct the prompt with segments inline
      const result: ParsedResponsePart[] = [];
      const workingPrompt = this.userPrompt;
      let currentPosition = 0;

      // Sort segments by their order of appearance (if they appear in the prompt)
      const sortedSegments = [...this.segments].sort((a, b) => {
        const indexA = workingPrompt.indexOf(a.text);
        const indexB = workingPrompt.indexOf(b.text);
        if (indexA === -1) {return 1;}
        if (indexB === -1) {return -1;}
        return indexA - indexB;
      });

      // Track how many segments we successfully matched
      let matchedSegments = 0;

      // Try to find each segment in the prompt and wrap it
      for (const segment of sortedSegments) {
        const segmentIndex = workingPrompt.indexOf(segment.text, currentPosition);

        if (segmentIndex !== -1) {
          matchedSegments++;
          // Add text before the segment
          if (segmentIndex > currentPosition) {
            result.push({
              text: workingPrompt.substring(currentPosition, segmentIndex),
              isSegment: false
            });
          }

          // Add the segment itself as a bracketed item
          result.push({
            text: segment.text,
            isSegment: true,
            segmentId: segment.id
          });

          currentPosition = segmentIndex + segment.text.length;
        }
      }

      // Add any remaining text
      if (currentPosition < workingPrompt.length) {
        result.push({
          text: workingPrompt.substring(currentPosition),
          isSegment: false
        });
      }

      // If we matched fewer segments than we have, use fallback approach
      // This handles cases where AI returns conceptual summaries instead of verbatim text
      if (matchedSegments < this.segments.length) {
        console.warn(`Only matched ${matchedSegments}/${this.segments.length} segments in userPrompt. Using fallback display.`);

        // Clear the result and rebuild showing all segments with their conceptual text
        result.length = 0;

        // Show all segments as hoverable conceptual descriptions
        this.segments.forEach((segment, index) => {
          if (index > 0) {
            result.push({ text: ' ', isSegment: false });
          }
          result.push({
            text: segment.text,
            isSegment: true,
            segmentId: segment.id
          });
        });
      }

      return result;
    }
  },
  mounted() {
    // Clean mount - no canvas to update
  },
  beforeUnmount() {
    // Clean unmount
  },
  methods: {
    findSegmentId(text: string): number | null {
      // Find the segment ID that matches this text
      const segment = this.segments.find(s => s.text === text);
      return segment ? segment.id : null;
    },

    setActiveSegment(segmentId: number): void {
      this.activeSegment = segmentId;
    },

    clearActiveSegment(): void {
      this.activeSegment = null;
    },

    toggleSegment(segmentId: number): void {
      this.activeSegment = this.activeSegment === segmentId ? null : segmentId;
    },

    getSegmentColor(segmentId: number): string {
      // Read segment color from CSS variables (theme-aware)
      const index = ((segmentId - 1) % 6) + 1;
      return getComputedStyle(document.documentElement)
        .getPropertyValue(`--color-segment-${index}`).trim() || '#9f7aea';
    },

    getSegmentNumber(segmentId: number): number {
      // Find the segment's display number (1-indexed)
      const index = this.segments.findIndex(s => s.id === segmentId);
      return index + 1;
    },

    getLineSegmentId(lineNumber: number): number | null {
      // Find which segment this line belongs to
      const segment = this.segments.find(s =>
        s.code_lines && s.code_lines.includes(lineNumber)
      );
      return segment ? segment.id : null;
    },

    isLineHighlighted(lineNumber: number): boolean {
      if (!this.activeSegment) {
        return false;
      }
      const segment = this.segments.find(s => s.id === this.activeSegment);
      return !!segment?.code_lines?.includes(lineNumber);
    },

    tokenClass(type: string): string {
      // Convert Ace token types like 'keyword.operator' to CSS classes 'ace_keyword ace_operator'
      if (!type || type === 'text' || type === 'identifier') {
        return '';
      }
      return type.split('.').map(part => `ace_${part}`).join(' ');
    },

    getLineClass(lineNumber: number): string[] {
      const classes: string[] = ['code-line'];

      if (this.activeSegment) {
        const activeSegmentData = this.segments.find(s => s.id === this.activeSegment);
        if (activeSegmentData && activeSegmentData.code_lines && activeSegmentData.code_lines.includes(lineNumber)) {
          classes.push('highlighted');
        } else {
          classes.push('dimmed');
        }
      }

      return classes;
    }

  }
});
</script>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.segment-mapping {
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  overflow: hidden;
  border: 1px solid var(--color-bg-input);
}

.mapping-grid-simplified {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 300px;
  gap: 0;
}

/* Panels */
.response-panel,
.code-panel {
  padding: var(--spacing-md) var(--spacing-sm);
  overflow-y: auto;
  max-height: 60vh;
  min-height: 300px;
}

.response-panel {
  background: var(--color-bg-section);
  border-right: 1px solid var(--color-bg-input);
}

.code-panel {
  background: var(--color-bg-panel);
  border-left: 1px solid var(--color-bg-input);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
  padding-bottom: var(--spacing-xs);
  border-bottom: 2px solid var(--color-bg-input);
}

.title-icon {
  font-size: var(--font-size-base);
}

/* Response Text Styling */
.response-text {
  font-size: var(--font-size-sm);
  line-height: 2;
  color: var(--color-text-primary);
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-bg-border);
  margin-top: var(--spacing-sm);
}

.segment-span {
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  display: inline;
  margin: 0 2px;
}

/* Subway Map: Circular outlined marker */
.segment-marker {
  display: inline-block;
  text-align: center;
  line-height: 20px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid;
  background: transparent;
  font-size: 12px;
  font-weight: 700;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  vertical-align: middle;
  margin-right: 4px;
}

.segment-text {
  transition: all 0.2s ease;
  display: inline;
  font-size: var(--font-size-base);
  border-bottom: 2px solid;
  padding-bottom: 1px;
}

/* Hover: invert circle, contrasting text */
.segment-span:hover .segment-marker {
  background: var(--segment-bg-color) !important;
  color: var(--color-text-on-filled) !important;
}

/* Active state */
.segment-span.active .segment-marker {
  background: var(--segment-bg-color) !important;
  color: var(--color-text-on-filled) !important;
}


/* Code Display */
.code-display {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--font-size-sm);
  line-height: 1.4;
  background: var(--color-bg-dark);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-bg-border);
  overflow-x: auto;
}

.code-line {
  display: flex;
  align-items: flex-start;
  padding: 2px 0;
  transition: var(--transition-fast);
  position: relative;
  min-height: 20px;
}

.code-line:hover .line-number {
  background: var(--color-bg-input);
}

.code-line:hover .line-content {
  background: var(--color-overlay-subtle);
}

.code-line.highlighted {
  background: var(--color-primary-overlay);
}

.code-line.highlighted .line-number {
  background: var(--color-primary-overlay);
}

.code-line.highlighted .line-content {
  background: var(--color-primary-overlay);
}

.code-line.dimmed {
  opacity: 0.4;
}

.code-line.dimmed .line-number[data-segment-id] {
  opacity: 0.5;
}

/* Subway Map: Line number with colored stripe */
.line-number {
  display: inline-block;
  width: 40px;
  text-align: right;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  user-select: none;
  flex-shrink: 0;
  background: var(--color-bg-section);
  padding: 2px 8px 2px 4px;
  border-right: 1px solid var(--color-bg-border);
  border-left: 3px solid transparent;
  margin-right: 12px;
  font-weight: normal;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Subway Map: Colored lane stripe on segments */
.line-number[data-segment-id] {
  border-left-style: solid;
}

/* Active state: wider stripe and subtle background tint */
.code-line.highlighted .line-number[data-segment-id] {
  border-left-width: 6px;
  background: var(--color-overlay-strong);
}

.line-content {
  color: var(--color-text-primary);
  flex: 1;
  white-space: pre;
  padding: 2px 4px;
  text-align: left;
  font-family: inherit;
}



/* Responsive */
@media (max-width: 1024px) {
  .mapping-grid-simplified {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
  }

  .response-panel,
  .code-panel {
    border: none;
    border-bottom: 1px solid var(--color-bg-input);
  }

  .code-panel {
    border-bottom: none;
  }
}

@media (max-width: 768px) {
  .response-panel,
  .code-panel {
    padding: var(--spacing-md);
    max-height: 250px;
  }
}

/* Scrollbar styling */
.response-panel::-webkit-scrollbar,
.code-panel::-webkit-scrollbar {
  width: 4px;
}

.response-panel::-webkit-scrollbar-track,
.code-panel::-webkit-scrollbar-track {
  background: transparent;
}

.response-panel::-webkit-scrollbar-thumb,
.code-panel::-webkit-scrollbar-thumb {
  background: var(--color-bg-border);
  border-radius: 2px;
}

/* Syntax highlighting */
.line-content .ace_keyword { color: var(--color-syntax-keyword); }
.line-content .ace_keyword.ace_operator { color: var(--color-syntax-operator); }
.line-content .ace_string { color: var(--color-syntax-string); }
.line-content .ace_constant.ace_language.ace_escape { color: var(--color-syntax-string); }
.line-content .ace_comment { color: var(--color-syntax-comment); font-style: italic; }
.line-content .ace_constant.ace_numeric { color: var(--color-syntax-number); }
.line-content .ace_constant.ace_language { color: var(--color-syntax-number); }
.line-content .ace_support.ace_function { color: var(--color-syntax-builtin); }
.line-content .ace_variable.ace_language { color: var(--color-syntax-variable); }
.line-content .ace_punctuation,
.line-content .ace_paren.ace_lparen,
.line-content .ace_paren.ace_rparen { color: var(--color-syntax-punctuation); }

</style>
