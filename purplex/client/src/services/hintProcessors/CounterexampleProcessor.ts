/**
 * Counterexample Processor
 * Handles Counterexample hints that show as UI overlays for Refute problems
 */

import { log } from '../../utils/logger';
import {
  HintProcessor,
  HintRenderStrategy,
  HintResult,
  CounterexampleData
} from './types';

const logger = log.createComponentLogger('CounterexampleProcessor');

class CounterexampleProcessor implements HintProcessor<CounterexampleData> {
  strategy = HintRenderStrategy.OVERLAY_UI;

  processHint(hintData: CounterexampleData): HintResult {
    logger.debug('Processing Counterexample hint', hintData);

    try {
      const { input, explanation } = hintData;

      if (!input || typeof input !== 'object') {
        logger.warn('Invalid hint data: missing or invalid input');
        return {
          success: false,
          error: 'Missing counterexample input'
        };
      }

      logger.debug('Counterexample processing completed', {
        paramCount: Object.keys(input).length,
        hasExplanation: !!explanation
      });

      return {
        success: true,
        overlayComponent: 'CounterexampleOverlay',
        overlayProps: {
          input,
          explanation: explanation || ''
        },
        metadata: {
          strategy: HintRenderStrategy.OVERLAY_UI,
          canStack: true,
          affectsLineNumbers: false
        }
      };

    } catch (error) {
      logger.error('Counterexample processing error', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      return {
        success: false,
        error: errorMessage
      };
    }
  }
}

export default CounterexampleProcessor;
