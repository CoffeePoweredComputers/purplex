/**
 * Variable Fade Processor
 * Converts Variable Fade hints to code transformations with proper logging
 */

import { log } from '../../utils/logger';
import { 
  HintProcessor, 
  HintRenderStrategy, 
  HintResult, 
  VariableFadeData,
  EditorMarker 
} from './types';

const logger = log.createComponentLogger('VariableFadeProcessor');

class VariableFadeProcessor implements HintProcessor<VariableFadeData> {
  static strategy = HintRenderStrategy.MODIFY_CODE;
  static processHint(hintData: VariableFadeData): HintResult {
    logger.debug('Processing Variable Fade hint', hintData);

    try {
      const { code, variable_mappings, mappings } = hintData;
      const actualMappings = variable_mappings || mappings; // Support both formats
      
      if (!code || !actualMappings) {
        logger.warn('Invalid hint data: missing code or mappings');
        return { success: false, code: '', markers: [], error: 'Missing required data' };
      }

      let modifiedCode = code;
      const markers: EditorMarker[] = [];

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

        // Create markers for highlighting
        const lines = modifiedCode.split('\n');
        lines.forEach((line, lineIndex) => {
          if (line.includes(to)) {
            markers.push({
              startRow: lineIndex,
              startCol: line.indexOf(to),
              endRow: lineIndex,
              endCol: line.indexOf(to) + to.length,
              className: 'ace_variable-meaningful',
              type: 'text' as const
            });
          }
        });
      }

      logger.debug('Variable fade processing completed', {
        originalLength: code.length,
        modifiedLength: modifiedCode.length,
        markersCount: markers.length
      });

      return {
        success: true,
        code: modifiedCode,
        markers,
        metadata: {
          strategy: HintRenderStrategy.MODIFY_CODE,
          canStack: false,  // Cannot stack with other code modifications
          affectsLineNumbers: false  // Only replaces text, doesn't add lines
        }
      };

    } catch (error) {
      logger.error('Variable fade processing error', error);
      return { success: false, code: '', markers: [], error: error.message };
    }
  }

  static isValidVariableName(name: string): boolean {
    // Python variable name validation
    return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
  }
}

export default VariableFadeProcessor;