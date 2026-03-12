/**
 * Subgoal Highlight Processor
 * Inserts STEP comments into code for subgoal highlighting
 */

import { log } from '../../utils/logger';
import {
  EditorMarker,
  HintProcessor,
  HintRenderStrategy,
  HintResult,
  SubgoalData
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
        return { success: false, code: '', error: 'Missing code or subgoals array' };
      }

      // Use the addSubgoalComments method to insert comments
      const result = SubgoalHighlightProcessor.addSubgoalComments(code, subgoals);

      if (!result.success) {
        return result;
      }

      logger.debug(`Processed ${subgoals.length} subgoals`);

      // Add metadata to the result, preserving markers from addSubgoalComments
      return {
        ...result,
        metadata: {
          strategy: HintRenderStrategy.ANNOTATE_CODE,
          canStack: false,  // Cannot stack with other code modifications
          affectsLineNumbers: true,  // Comments change line numbers
          markers: result.metadata?.markers
        }
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      logger.error('Subgoal highlight processing error', errorMessage);
      return { success: false, code: '', error: errorMessage };
    }
  }

  static addSubgoalComments(code: string, subgoals: SubgoalData['subgoals']): HintResult {
    logger.debug('Adding subgoal comments to code');
    logger.debug('Original code:', {
      code,
      length: code.length,
      lineCount: code.split('\n').length,
      hasNewlines: code.includes('\n')
    });

    try {
      const lines = code.split('\n');
      const modifiedLines = [...lines];

      logger.debug('Original lines:', lines.map((line, idx) => ({
        lineNumber: idx + 1,
        content: line,
        length: line.length
      })));

      // Sort by line number (descending) to process from bottom to top
      const sortedSubgoals = [...subgoals]
        .map((sg, idx) => ({ subgoal: sg, originalIndex: idx }))
        .sort((a, b) => b.subgoal.line_start - a.subgoal.line_start);

      logger.debug('Sorted subgoals:', sortedSubgoals);

      // Track markers for editor highlighting (built bottom-up alongside code)
      const markers: EditorMarker[] = [];

      // Process each subgoal
      sortedSubgoals.forEach(({ subgoal, originalIndex }) => {

        // Get indenation of line that we are going to annotate
        const targetLine = modifiedLines[subgoal.line_start - 1] || '';
        const indentationMatch = targetLine.match(/^\s*/);
        const indentation = indentationMatch ? indentationMatch[0] : '';
        const stepNumber = originalIndex + 1;
        // Use explanation field from backend (the actual field that exists)
        const commentContent = subgoal.explanation || 'Subgoal';
        const commentText = indentation + (`# STEP ${stepNumber}: ${commentContent}`.replace(/[^\x20-\x7E]/g, ''));
        const insertPosition = subgoal.line_start - 1; // Convert to 0-based

        // Insert comment before the target line
        logger.debug(`Inserting comment at position ${insertPosition}:`, {
          commentText,
          targetLine,
          indentation: indentation.length,
          linesBeforeInsert: modifiedLines.length
        });

        modifiedLines.splice(insertPosition, 0, commentText);

        // Shift previously computed markers that are at or after the insert point
        for (const m of markers) {
          if (m.row >= insertPosition) {
            m.row += 1;
          }
        }

        // Mark the comment line
        markers.push({ row: insertPosition, className: 'ace_subgoal-comment' });

        // Mark code lines within this subgoal's range
        // After insertion, original line_start is now at index line_start (0-indexed)
        for (let line = subgoal.line_start; line <= subgoal.line_end; line++) {
          markers.push({ row: line, className: 'ace_subgoal-highlight' });
        }

        logger.debug(`After insertion:`, {
          linesAfterInsert: modifiedLines.length,
          insertedLine: modifiedLines[insertPosition],
          nextLine: modifiedLines[insertPosition + 1]
        });
      });

      const joinedLines = modifiedLines.join('\n');

      // Sort markers by row for consistent ordering
      markers.sort((a, b) => a.row - b.row);

      logger.debug('Final result:', {
        modifiedCode: joinedLines,
        length: joinedLines.length,
        lineCount: modifiedLines.length,
        firstFewLines: modifiedLines.slice(0, 5),
        hasNewlines: joinedLines.includes('\n'),
        markerCount: markers.length
      });

      return {
        success: true,
        code: joinedLines,
        metadata: {
          strategy: HintRenderStrategy.ANNOTATE_CODE,
          canStack: false,
          affectsLineNumbers: true,
          markers
        }
      };

    } catch (error) {
      logger.error('Failed to add subgoal comments', error);
      return { success: false, code };
    }
  }
}

export default SubgoalHighlightProcessor;
