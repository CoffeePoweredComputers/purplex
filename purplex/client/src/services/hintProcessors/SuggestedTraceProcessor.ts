/**
 * Suggested Trace Processor
 * Handles Suggested Trace hints that show as UI overlays
 */

import { log } from '../../utils/logger';
import {
  HintProcessor,
  HintRenderStrategy,
  HintResult,
  SuggestedTraceData
} from './types';

const logger = log.createComponentLogger('SuggestedTraceProcessor');

class SuggestedTraceProcessor implements HintProcessor<SuggestedTraceData> {
  strategy = HintRenderStrategy.OVERLAY_UI;

  processHint(hintData: SuggestedTraceData): HintResult {
    logger.debug('Processing Suggested Trace hint', hintData);

    try {
      const { suggested_call, explanation, expected_output } = hintData;

      if (!suggested_call) {
        logger.warn('Invalid hint data: missing suggested_call');
        return {
          success: false,
          error: 'Missing suggested function call'
        };
      }

      logger.debug('Suggested trace processing completed', {
        hasExplanation: !!explanation,
        hasExpectedOutput: !!expected_output
      });

      return {
        success: true,
        overlayComponent: 'SuggestedTraceOverlay',
        overlayProps: {
          suggestedCall: suggested_call,
          explanation: explanation || '',
          expectedOutput: expected_output
        },
        metadata: {
          strategy: HintRenderStrategy.OVERLAY_UI,
          canStack: true,  // Can show alongside other hints
          affectsLineNumbers: false  // Doesn't modify code
        }
      };

    } catch (error) {
      logger.error('Suggested trace processing error', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      return {
        success: false,
        error: errorMessage
      };
    }
  }
}

export default SuggestedTraceProcessor;
