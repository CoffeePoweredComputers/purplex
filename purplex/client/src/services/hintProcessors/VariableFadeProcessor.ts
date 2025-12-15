/**
 * Variable Fade Processor
 * Converts Variable Fade hints to code transformations with proper logging
 */

import { log } from '../../utils/logger';
import {
  HintProcessor,
  HintRenderStrategy,
  HintResult,
  VariableFadeData
} from './types';

const logger = log.createComponentLogger('VariableFadeProcessor');

class VariableFadeProcessor implements HintProcessor<VariableFadeData> {
  strategy = HintRenderStrategy.MODIFY_CODE;
  processHint(hintData: VariableFadeData): HintResult {
    logger.debug('Processing Variable Fade hint', hintData);

    try {
      const { code, variable_mappings, mappings } = hintData;
      const actualMappings = variable_mappings || mappings; // Support both formats

      if (!code || !actualMappings) {
        logger.warn('Invalid hint data: missing code or mappings');
        return { success: false, code: '', error: 'Missing required data' };
      }

      let modifiedCode = code;

      // Process each variable mapping
      for (const mapping of actualMappings) {
        if (!mapping.from || !mapping.to) {
          logger.warn('Skipping invalid mapping', mapping);
          continue;
        }

        const { from, to } = mapping;
        if (!this.isValidVariableName(from) || !this.isValidVariableName(to)) {
          logger.warn(`Invalid variable names: ${from} -> ${to}`);
          continue;
        }

        // Replace variables in code
        const regex = new RegExp(`\\b${from}\\b`, 'g');
        modifiedCode = modifiedCode.replace(regex, to);
      }

      logger.debug('Variable fade processing completed', {
        originalLength: code.length,
        modifiedLength: modifiedCode.length
      });

      return {
        success: true,
        code: modifiedCode,
        metadata: {
          strategy: HintRenderStrategy.MODIFY_CODE,
          canStack: false,  // Cannot stack with other code modifications
          affectsLineNumbers: false  // Only replaces text, doesn't add lines
        }
      };

    } catch (error) {
      logger.error('Variable fade processing error', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      return { success: false, code: '', error: errorMessage };
    }
  }

  isValidVariableName(name: string): boolean {
    // Check for null/undefined
    if (!name || typeof name !== 'string') {
      return false;
    }
    // Python variable name validation
    return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
  }
}

export default VariableFadeProcessor;
