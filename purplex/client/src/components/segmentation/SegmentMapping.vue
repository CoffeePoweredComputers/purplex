<template>
  <div class="segment-mapping">
    <div class="mapping-grid-simplified">
      <!-- Left: Student Response with Inline Segments -->
      <div class="response-panel">
        <h4 class="panel-title">
          <span class="title-icon">💭</span>
          Your Explanation
        </h4>
        <div class="response-text">
          <span 
            v-for="(part, index) in parsedResponse" 
            :key="`part-${index}`"
            :class="{ 
              'segment-span': part.isSegment,
              'active': part.isSegment && activeSegment === part.segmentId 
            }"
            @mouseenter="part.isSegment && setActiveSegment(part.segmentId)"
            @mouseleave="part.isSegment && clearActiveSegment()"
          >
            <template v-if="part.isSegment">[{{ part.text }}]</template>
            <template v-else>{{ part.text }}</template>
          </span>
        </div>
      </div>
      
      <!-- Right: Code with Highlights -->
      <div class="code-panel">
        <h4 class="panel-title">
          <span class="title-icon">📝</span>
          Reference Code
        </h4>
        <div class="code-display">
          <div 
            v-for="(line, index) in codeLines"
            :key="index"
            class="code-line"
            :class="getLineClass(index + 1)"
          >
            <span class="line-number">{{ index + 1 }}</span>
            <code class="line-content">{{ line }}</code>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue';

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
    
    parsedResponse(): ParsedResponsePart[] {
      
      if (!this.userPrompt) {
        return [{ text: '', isSegment: false }];
      }
      
      // Simple approach: Just display the whole prompt as one piece for now
      // to verify the component is receiving data
      if (!this.segments || this.segments.length === 0) {
        return [{ text: this.userPrompt, isSegment: false }];
      }
      
      // Debug logging
      console.log('Parsing response with segments:', this.segments);
      console.log('User prompt:', this.userPrompt);
      
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
      
      // Try to find each segment in the prompt and wrap it
      for (const segment of sortedSegments) {
        const segmentIndex = workingPrompt.indexOf(segment.text, currentPosition);
        
        if (segmentIndex !== -1) {
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
      
      // If no segments were found in the text, we need a different approach
      // The segments ARE the text, just broken into pieces
      if (result.length === 1 && !result[0].isSegment) {
        // Clear the result and rebuild using just the segments
        result.length = 0;
        
        this.segments.forEach((segment, index) => {
          if (index > 0) {
            // Add a space between segments
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
      // Debug the segment data
      const segment = this.segments.find(s => s.id === segmentId);
      if (segment) {
        console.log('Active segment:', segmentId, segment);
        console.log('Code lines type:', typeof segment.code_lines);
        console.log('Code lines value:', segment.code_lines);
        // Try to expand proxy if it's a proxy
        try {
          console.log('Code lines array:', Array.from(segment.code_lines));
        } catch (e) {
          console.log('Could not convert to array:', e);
        }
      }
    },
    
    clearActiveSegment(): void {
      this.activeSegment = null;
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
  background: var(--color-bg-hover);
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
  line-height: 1.8;
  color: var(--color-text-primary);
  padding: var(--spacing-md);
  background: var(--color-bg-panel);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-bg-border);
  margin-top: var(--spacing-sm);
}

.segment-span {
  color: var(--color-primary-gradient-start);
  cursor: pointer;
  transition: var(--transition-fast);
  position: relative;
  padding: 2px 4px;
  margin: 0 2px;
  border-radius: var(--radius-xs);
}

.segment-span:hover {
  background: rgba(102, 126, 234, 0.1);
  color: var(--color-primary);
}

.segment-span.active {
  background: rgba(102, 126, 234, 0.2);
  color: var(--color-primary);
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
  background: rgba(255, 255, 255, 0.02);
}

.code-line.highlighted {
  background: rgba(102, 126, 234, 0.1);
}

.code-line.highlighted .line-number {
  background: rgba(102, 126, 234, 0.2);
  border-left: 3px solid var(--color-primary-gradient-start);
}

.code-line.highlighted .line-content {
  background: rgba(102, 126, 234, 0.1);
}

.code-line.dimmed {
  opacity: 0.4;
}

.line-number {
  display: inline-block;
  width: 40px;
  text-align: right;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  user-select: none;
  flex-shrink: 0;
  background: var(--color-bg-hover);
  padding: 2px 8px 2px 4px;
  border-right: 1px solid var(--color-bg-border);
  margin-right: 12px;
  font-weight: normal;
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
</style>