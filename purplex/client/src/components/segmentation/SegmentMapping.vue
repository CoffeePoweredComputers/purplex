<template>
  <div class="segment-mapping">
    <div class="mapping-grid">
      <!-- Left: Segments -->
      <div class="segments-panel">
        <h4 class="panel-title">
          <span class="title-icon">💭</span>
          Your Explanation
        </h4>
        <div class="segments-list">
          <div 
            v-for="segment in segments" 
            :key="segment.id"
            class="segment-item"
            :class="{ active: activeSegment === segment.id }"
            @mouseenter="setActiveSegment(segment.id)"
            @mouseleave="clearActiveSegment"
            @click="toggleSegment(segment.id)"
          >
            <span class="segment-id">{{ segment.id }}</span>
            <span class="segment-text">{{ segment.text }}</span>
            <span class="segment-lines-count">
              → {{ segment.code_lines.length }} line{{ segment.code_lines.length !== 1 ? 's' : '' }}
            </span>
          </div>
        </div>
      </div>
      
      <!-- Center: Connection Visualization -->
      <div class="connection-panel">
        <svg 
          class="connection-canvas" 
          ref="canvas"
          :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="connectionGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" :style="`stop-color:${connectionColor};stop-opacity:0.8`" />
              <stop offset="50%" :style="`stop-color:${connectionColor};stop-opacity:1`" />
              <stop offset="100%" :style="`stop-color:${connectionColor};stop-opacity:0.8`" />
            </linearGradient>
          </defs>
          
          <path 
            v-for="segment in segments"
            :key="`path-${segment.id}`"
            :d="getConnectionPath(segment)"
            class="connection-line"
            :class="{ 
              active: activeSegment === segment.id,
              selected: selectedSegment === segment.id 
            }"
            stroke="url(#connectionGradient)"
          />
        </svg>
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
            @mouseenter="highlightConnectedSegments(index + 1)"
            @mouseleave="clearLineHighlight"
          >
            <span class="line-number">{{ index + 1 }}</span>
            <code class="line-content">{{ line }}</code>
            <div 
              v-if="getLineConnections(index + 1).length > 0"
              class="line-connections"
            >
              <span 
                v-for="segId in getLineConnections(index + 1)"
                :key="segId"
                class="connection-badge"
                :class="{ active: activeSegment === segId }"
              >
                {{ segId }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SegmentMapping',
  props: {
    segments: {
      type: Array,
      required: true,
      default: () => []
    },
    referenceCode: {
      type: String,
      required: true,
      default: ''
    }
  },
  data() {
    return {
      activeSegment: null,
      selectedSegment: null,
      canvasWidth: 200,
      canvasHeight: 400,
      connectionColor: '#667eea'
    };
  },
  computed: {
    codeLines() {
      return this.referenceCode.split('\n').filter(line => line.trim() !== '');
    }
  },
  mounted() {
    this.updateCanvasSize();
    window.addEventListener('resize', this.updateCanvasSize);
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.updateCanvasSize);
  },
  methods: {
    setActiveSegment(segmentId) {
      this.activeSegment = segmentId;
    },
    
    clearActiveSegment() {
      this.activeSegment = null;
    },
    
    toggleSegment(segmentId) {
      this.selectedSegment = this.selectedSegment === segmentId ? null : segmentId;
    },
    
    highlightConnectedSegments(lineNumber) {
      const connectedSegment = this.segments.find(seg => 
        seg.code_lines.includes(lineNumber)
      );
      if (connectedSegment) {
        this.setActiveSegment(connectedSegment.id);
      }
    },
    
    clearLineHighlight() {
      this.clearActiveSegment();
    },
    
    getLineClass(lineNumber) {
      const classes = ['code-line'];
      
      if (this.activeSegment) {
        const activeSegmentData = this.segments.find(s => s.id === this.activeSegment);
        if (activeSegmentData && activeSegmentData.code_lines.includes(lineNumber)) {
          classes.push('highlighted');
        } else {
          classes.push('dimmed');
        }
      }
      
      return classes;
    },
    
    getLineConnections(lineNumber) {
      return this.segments
        .filter(segment => segment.code_lines.includes(lineNumber))
        .map(segment => segment.id);
    },
    
    getConnectionPath(segment) {
      if (!this.$refs.canvas) return '';
      
      // Simple curved path from left to right
      const segmentY = (segment.id - 1) * 40 + 20; // Approximate segment position
      const codeY = segment.code_lines.length > 0 ? 
        (segment.code_lines[0] - 1) * 25 + 12 : segmentY; // Approximate code line position
      
      const startX = 10;
      const endX = this.canvasWidth - 10;
      const controlX1 = this.canvasWidth * 0.3;
      const controlX2 = this.canvasWidth * 0.7;
      
      return `M ${startX} ${segmentY} C ${controlX1} ${segmentY}, ${controlX2} ${codeY}, ${endX} ${codeY}`;
    },
    
    updateCanvasSize() {
      this.$nextTick(() => {
        if (this.$refs.canvas && this.$refs.canvas.parentElement) {
          const container = this.$refs.canvas.parentElement;
          this.canvasWidth = container.offsetWidth;
          this.canvasHeight = Math.max(
            this.segments.length * 40,
            this.codeLines.length * 25,
            200
          );
        }
      });
    }
  }
};
</script>

<style scoped>
.segment-mapping {
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  overflow: hidden;
  border: 1px solid var(--color-bg-input);
}

.mapping-grid {
  display: grid;
  grid-template-columns: 1fr 200px 1fr;
  min-height: 300px;
}

/* Panels */
.segments-panel,
.code-panel {
  padding: var(--spacing-lg);
  overflow-y: auto;
  max-height: 400px;
}

.segments-panel {
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
  margin: 0 0 var(--spacing-lg) 0;
  padding-bottom: var(--spacing-sm);
  border-bottom: 2px solid var(--color-bg-input);
}

.title-icon {
  font-size: var(--font-size-base);
}

/* Segments */
.segments-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.segment-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  position: relative;
}

.segment-item:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.segment-item.active {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.segment-id {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: var(--color-primary-gradient-start);
  color: white;
  border-radius: var(--radius-circle);
  font-size: var(--font-size-xs);
  font-weight: 700;
  flex-shrink: 0;
}

.segment-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: 1.4;
  word-wrap: break-word;
}

.segment-lines-count {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-style: italic;
}

/* Connection Canvas */
.connection-panel {
  position: relative;
  background: var(--color-bg-dark);
  display: flex;
  align-items: center;
  justify-content: center;
}

.connection-canvas {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.connection-line {
  fill: none;
  stroke-width: 2;
  opacity: 0.3;
  transition: var(--transition-base);
  stroke-dasharray: 5, 5;
  animation: dashMove 2s linear infinite;
}

.connection-line.active {
  stroke-width: 3;
  opacity: 1;
  stroke-dasharray: none;
  animation: none;
  filter: drop-shadow(0 0 4px var(--color-primary-gradient-start));
}

.connection-line.selected {
  stroke-width: 4;
  opacity: 1;
  stroke-dasharray: none;
  animation: none;
}

/* Code Display */
.code-display {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--font-size-sm);
  line-height: 1.6;
}

.code-line {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  transition: var(--transition-fast);
  position: relative;
  min-height: 25px;
}

.code-line:hover {
  background: var(--color-bg-hover);
}

.code-line.highlighted {
  background: rgba(102, 126, 234, 0.15);
  border-left: 3px solid var(--color-primary-gradient-start);
  padding-left: calc(var(--spacing-sm) - 3px);
}

.code-line.dimmed {
  opacity: 0.4;
}

.line-number {
  display: inline-block;
  width: 24px;
  text-align: right;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  user-select: none;
  flex-shrink: 0;
}

.line-content {
  color: var(--color-text-primary);
  flex: 1;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.line-connections {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
}

.connection-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  background: var(--color-bg-border);
  color: var(--color-text-muted);
  border-radius: var(--radius-circle);
  font-size: var(--font-size-xs);
  font-weight: 600;
  transition: var(--transition-fast);
}

.connection-badge.active {
  background: var(--color-primary-gradient-start);
  color: white;
}

/* Animations */
@keyframes dashMove {
  to {
    stroke-dashoffset: -10;
  }
}

/* Responsive */
@media (max-width: 1024px) {
  .mapping-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
  }
  
  .connection-panel {
    display: none; /* Hide connections on mobile */
  }
  
  .segments-panel,
  .code-panel {
    border: none;
    border-bottom: 1px solid var(--color-bg-input);
  }
  
  .code-panel {
    border-bottom: none;
  }
}

@media (max-width: 768px) {
  .segments-panel,
  .code-panel {
    padding: var(--spacing-md);
    max-height: 250px;
  }
  
  .segment-item {
    padding: var(--spacing-sm);
  }
  
  .code-line {
    font-size: var(--font-size-xs);
  }
}

/* Scrollbar styling */
.segments-panel::-webkit-scrollbar,
.code-panel::-webkit-scrollbar {
  width: 4px;
}

.segments-panel::-webkit-scrollbar-track,
.code-panel::-webkit-scrollbar-track {
  background: transparent;
}

.segments-panel::-webkit-scrollbar-thumb,
.code-panel::-webkit-scrollbar-thumb {
  background: var(--color-bg-border);
  border-radius: 2px;
}
</style>