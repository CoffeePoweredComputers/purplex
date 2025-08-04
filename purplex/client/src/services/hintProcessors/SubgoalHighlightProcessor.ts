/**
 * Subgoal Highlight Processor
 * Converts Subgoal Highlighting hints to code markers with proper logging
 */

import { log } from '../../utils/logger';
import { 
  HintProcessor, 
  HintRenderStrategy, 
  HintResult, 
  SubgoalData,
  EditorMarker 
} from './types';

const logger = log.createComponentLogger('SubgoalHighlightProcessor');

class SubgoalHighlightProcessor implements HintProcessor<SubgoalData> {
  strategy = HintRenderStrategy.ANNOTATE_CODE;
  
  processHint(hintData: SubgoalData): HintResult {
    logger.debug('Processing Subgoal Highlight hint', hintData);

    try {
      const { code, subgoals } = hintData;
      
      if (!code || !subgoals || !Array.isArray(subgoals)) {
        logger.warn('Invalid hint data: missing code or subgoals array');
        return { success: false, code: '', markers: [], error: 'Missing code or subgoals array' };
      }

      // Use the addSubgoalComments method to insert comments and get markers
      const result = SubgoalHighlightProcessor.addSubgoalComments(code, subgoals);
      
      if (!result.success) {
        return result;
      }

      logger.debug(`Processed ${subgoals.length} subgoals with ${result.markers?.length || 0} markers`);

      // Add metadata to the result
      return {
        ...result,
        metadata: {
          strategy: HintRenderStrategy.ANNOTATE_CODE,
          canStack: false,  // Cannot stack with other code modifications
          affectsLineNumbers: true  // Comments change line numbers
        }
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      logger.error('Subgoal highlight processing error', errorMessage);
      return { success: false, code: '', markers: [], error: errorMessage };
    }
  }

  static createSubgoalMarker(subgoal: any, index: number): EditorMarker {
    return {
      startRow: subgoal.line_start - 1,
      startCol: 0,
      endRow: subgoal.line_end - 1,
      endCol: 0,
      className: `subgoal-marker subgoal-${index}`,
      type: 'background',
      subgoalIndex: index,
      comment: subgoal.comment || subgoal.title || ''
    };
  }

  static addSubgoalComments(code: string, subgoals: SubgoalData['subgoals']): HintResult {
    logger.debug('Adding subgoal comments to code');
    
    try {
      const lines = code.split('\n');
      const modifiedLines = [...lines];
      const markers: EditorMarker[] = [];
      
      // Sort by line number (descending) to process from bottom to top
      const sortedSubgoals = [...subgoals]
        .map((sg, idx) => ({ subgoal: sg, originalIndex: idx }))
        .sort((a, b) => b.subgoal.line_start - a.subgoal.line_start);
      
      // Process each subgoal
      sortedSubgoals.forEach(({ subgoal, originalIndex }) => {
  
        // Get indenation of line that we are going to annotate
        const targetLine = modifiedLines[subgoal.line_start - 1] || '';
        const indentationMatch = targetLine.match(/^\s*/);
        const indentation = indentationMatch ? indentationMatch[0] : '';
        const stepNumber = originalIndex + 1;
        const commentText = indentation + `# STEP ${stepNumber}: ${subgoal.title || subgoal.comment || 'Subgoal'}`;
        const insertPosition = subgoal.line_start - 1; // Convert to 0-based
        
        // Insert comment before the target line
        modifiedLines.splice(insertPosition, 0, commentText);
        
        logger.debug(`Subgoal ${originalIndex}: inserted "${commentText}" at position ${insertPosition}`);
      });
      
      // Now create markers based on final positions
      // Re-sort by ascending order for marker creation
      const ascendingSubgoals = [...subgoals]
        .map((sg, idx) => ({ subgoal: sg, originalIndex: idx }))
        .sort((a, b) => a.subgoal.line_start - b.subgoal.line_start);
      
      let offsetSoFar = 0;
      ascendingSubgoals.forEach(({ subgoal, originalIndex }) => {
        const commentRow = subgoal.line_start - 1 + offsetSoFar;

        // compute horizontal space for the comment line based on foward whitespace of last line
        const lastLine = modifiedLines[commentRow + 1] || '';
        const whitespaceMatch = lastLine.match(/^\s*/);
        const forwardWhitespace = whitespaceMatch ? whitespaceMatch[0].length : 0;
        
        // Marker for the comment line
        markers.push({
          startRow: commentRow,
          startCol: forwardWhitespace,
          endRow: commentRow,
          endCol: forwardWhitespace,
          className: `ace_subgoal-comment subgoal-${originalIndex}`,
          type: 'fullLine'
        });
        
        // Markers for the highlighted code lines
        for (let i = 0; i <= subgoal.line_end - subgoal.line_start; i++) {
          markers.push({
            startRow: commentRow + 1 + i,
            startCol: forwardWhitespace,
            endRow: commentRow + 1 + i,
            endCol: forwardWhitespace,
            className: `ace_subgoal-highlight subgoal-${originalIndex}`,
            type: 'fullLine'
          });
        }
        
        offsetSoFar++;
        
        logger.debug(`Subgoal ${originalIndex}: comment at ${commentRow}, highlighting ${commentRow + 1} to ${commentRow + 1 + (subgoal.line_end - subgoal.line_start)}`);
      });
      
      return {
        success: true,
        code: modifiedLines.join('\n'),
        markers,
        metadata: {
          strategy: HintRenderStrategy.ANNOTATE_CODE,
          canStack: false,
          affectsLineNumbers: true
        }
      };

    } catch (error) {
      logger.error('Failed to add subgoal comments', error);
      return { success: false, code, markers: [] };
    }
  }
}

export default SubgoalHighlightProcessor;
