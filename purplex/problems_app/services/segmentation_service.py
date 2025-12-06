"""Segmentation service for prompt analysis."""
import time
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SegmentationService:
    """
    Service for prompt segmentation analysis using AI.

    Supports both Llama and OpenAI providers via configuration.
    Provider is selected via AI_PROVIDER setting ('llama' or 'openai').
    Fails immediately if the configured provider is unavailable - no fallback.
    """

    def __init__(self):
        # Determine which provider to use
        self.provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()

        # Initialize OpenAI
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.openai_model = getattr(settings, 'GPT_MODEL', 'gpt-4o-mini')
        if self.openai_api_key:
            import openai
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        else:
            self.openai_client = None

        # Initialize Llama
        self.llama_api_key = getattr(settings, 'LLAMA_API_KEY', None)
        self.llama_model = getattr(settings, 'LLAMA_MODEL', 'meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8')
        if self.llama_api_key:
            try:
                from llama_api_client import LlamaAPIClient
                self.llama_client = LlamaAPIClient(api_key=self.llama_api_key)
            except ImportError:
                logger.warning("llama-api-client not installed, Llama provider unavailable")
                self.llama_client = None
        else:
            self.llama_client = None

        # Select active client based on provider setting
        self._select_client()

    def _select_client(self):
        """Select which client to use based on configuration"""
        if self.provider == 'llama' and self.llama_client:
            self.client = self.llama_client
            self.model_name = self.llama_model
            logger.info(f"✅ Using Llama API provider for segmentation (model: {self.llama_model})")
        elif self.provider == 'openai' and self.openai_client:
            self.client = self.openai_client
            self.model_name = self.openai_model
            logger.info(f"✅ Using OpenAI API provider for segmentation (model: {self.openai_model})")
        else:
            self.client = None
            self.model_name = None
            logger.warning(f"⚠️  No valid AI provider configured for segmentation (provider={self.provider})")

    def _call_ai(self, messages, max_tokens=1500, temperature=0.3):
        """
        Unified AI call that handles both Llama and OpenAI APIs.
        Raises exception immediately on failure - no fallback.
        Uses JSON mode/schema to enforce structured output.
        """
        try:
            if self.provider == 'llama':
                # Llama API call with JSON Schema for strict validation
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "SegmentationResponse",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "segments": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "text": {"type": "string"},
                                                "code_lines": {
                                                    "type": "array",
                                                    "items": {"type": "integer"}
                                                }
                                            },
                                            "required": ["id", "text", "code_lines"]
                                        }
                                    }
                                },
                                "required": ["segments"]
                            }
                        }
                    }
                )
                content = response.completion_message.content.text
                logger.info(f"🦙 Llama API call successful with JSON schema (segmentation, model: {self.model_name})")

            else:  # openai
                # OpenAI API call with JSON mode
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format={"type": "json_object"}  # Enforce JSON output
                )
                content = response.choices[0].message.content
                logger.info(f"🤖 OpenAI API call successful with JSON mode (segmentation, model: {self.model_name})")

            return content

        except Exception as e:
            logger.error(f"❌ {self.provider.upper()} API call failed (segmentation): {str(e)}")
            raise  # Fail immediately - no fallback
    
    def segment_prompt(self, user_prompt: str, reference_code: str, problem_config: dict = None) -> dict:
        """
        Segment user prompt and map to code lines using AI (Llama or OpenAI)

        Args:
            user_prompt: User's explanation of the code
            reference_code: Reference solution code
            problem_config: Problem-specific segmentation configuration

        Returns:
            {
                'success': bool,
                'segments': [{'id': int, 'text': str, 'code_lines': [int]}],
                'segment_count': int,
                'comprehension_level': str,
                'feedback': str,
                'processing_time': float,
                'error': str (if failed)
            }
        """
        start_time = time.time()

        if not self.client:
            return {
                'success': False,
                'error': f'No AI provider configured for segmentation (provider={self.provider})',
                'segments': [],
                'groups': [],
                'segment_count': 0,
                'comprehension_level': 'unknown',
                'feedback': '',
                'processing_time': 0.0
            }

        try:
            # Get configuration values
            config = problem_config or {}
            threshold = config.get('threshold', 2)
            custom_examples = config.get('examples', {})

            # Create segmentation prompt with few-shot examples
            system_prompt = self._create_segmentation_prompt(reference_code, custom_examples)

            # Make API call using unified wrapper (handles both Llama and OpenAI)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please analyze this prompt: {user_prompt}"}
            ]

            content = self._call_ai(
                messages=messages,
                max_tokens=1500,
                temperature=0.0
            )

            # Log raw AI response for debugging
            self._log_segmentation_debug(user_prompt, reference_code, content)
            
            # Parse the response into structured segments
            segments_data = self._parse_segments(content, reference_code, user_prompt)
            
            if not segments_data['success']:
                return {
                    'success': False,
                    'error': segments_data['error'],
                    'segments': [],
                    'groups': [],
                    'segment_count': 0,
                    'comprehension_level': 'unknown',
                    'feedback': '',
                    'processing_time': time.time() - start_time
                }
            
            segments = segments_data['segments']
            groups = segments_data.get('groups', [])  # EiPL Grader format
            segment_count = len(segments)
            
            # Determine comprehension level and feedback
            level, feedback = self._determine_comprehension_level(segment_count, threshold, config)

            result = {
                'success': True,
                'segments': segments,
                'groups': groups,  # Include EiPL Grader format
                'segment_count': segment_count,
                'comprehension_level': level,
                'feedback': feedback,
                'processing_time': time.time() - start_time,
                'error': None
            }

            # Log the final result for debugging
            self._log_segmentation_result(result, user_prompt)

            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'segments': [],
                'groups': [],
                'segment_count': 0,
                'comprehension_level': 'unknown',
                'feedback': '',
                'processing_time': time.time() - start_time
            }
    
    def _create_segmentation_prompt(self, reference_code: str, custom_examples: dict = None) -> str:
        """Build few-shot prompt with examples for consistent one-to-one segmentation"""

        # Start with base prompt
        prompt_parts = ["""# Task:
Analyze the student's explanation and map conceptual segments to corresponding code sections with STRICT one-to-one correspondence.

# CRITICAL ONE-TO-ONE MAPPING RULES:
1. Each segment of the explanation maps to EXACTLY ONE distinct code section
2. Each code line can belong to ONLY ONE segment (no overlapping)
3. Once a line is assigned to a segment, it CANNOT be reused
4. Focus on conceptual units, not word-for-word extraction
5. Segments should represent complete thoughts or logical steps

# How to Segment:
1. Identify distinct conceptual units in the student's explanation
2. For each concept, find its corresponding code section
3. Assign line numbers ensuring NO OVERLAPS between segments
4. Each line of code belongs to at most one segment
5. Not all explanation needs to be segmented
6. Not all code needs to be mapped

# Two Comprehension Levels:
1. Relational (Good): 1-2 segments showing high-level understanding of overall purpose
2. Multi-structural (Needs Work): 3+ segments showing line-by-line procedural thinking

REFERENCE CODE:
```python
{}
```""".format(reference_code)]
        
        # Add examples if provided
        if custom_examples:
            prompt_parts.append("\nSEGMENTATION EXAMPLES:")
            
            # Add relational example if it exists
            if 'relational' in custom_examples and self._is_valid_example(custom_examples['relational']):
                example = custom_examples['relational']
                prompt_parts.append("\nRELATIONAL (High-level understanding):")
                prompt_parts.append(f'Student prompt: "{example["prompt"]}"')
                prompt_parts.append("Segments:")
                prompt_parts.append(self._format_example_segments(example['segments'], example['code_lines']))
            
            # Add multi-structural example if it exists
            if 'multi_structural' in custom_examples and self._is_valid_example(custom_examples['multi_structural']):
                example = custom_examples['multi_structural']
                prompt_parts.append("\nMULTI-STRUCTURAL (Line-by-line description):")
                prompt_parts.append(f'Student prompt: "{example["prompt"]}"')
                prompt_parts.append("Segments:")
                prompt_parts.append(self._format_example_segments(example['segments'], example['code_lines']))
        
        # Add instructions
        prompt_parts.append("""
# ONE-TO-ONE MAPPING VALIDATION:
Before returning your response, verify:
- No line number appears in multiple segments
- Each segment has unique, non-overlapping line numbers
- Line assignments make logical sense

INSTRUCTIONS:
- Identify conceptual segments in the student's explanation
- Use the student's actual words for the "text" field (prefer verbatim when possible)
- Map each segment to its UNIQUE code lines (1-indexed)
- ENSURE NO LINE NUMBER APPEARS IN MULTIPLE SEGMENTS
- Return your analysis as JSON in this exact format:

{
    "segments": [
        {"id": 1, "text": "description of first concept", "code_lines": [1, 2]},
        {"id": 2, "text": "description of second concept", "code_lines": [3]}
    ]
}

CRITICAL: Each line number must appear in at most ONE segment. Overlapping line numbers will invalidate the segmentation.""")
        
        return '\n'.join(prompt_parts)
    
    def _is_valid_example(self, example: dict) -> bool:
        """Check if an example has all required fields"""
        required_fields = ['prompt', 'segments', 'code_lines']
        return all(field in example and example[field] for field in required_fields)
    
    def _format_example_segments(self, segments: list, code_lines: list) -> str:
        """Format example segments for the prompt"""
        formatted = []
        for i, (segment, lines) in enumerate(zip(segments, code_lines)):
            formatted.append(f'  {i+1}. "{segment}" -> lines {lines}')
        return '\n'.join(formatted)
    
    def _validate_segment_is_verbatim(self, segment_text: str, user_prompt: str) -> bool:
        """
        Validate that a segment text is an exact substring of the user prompt.
        
        Args:
            segment_text: The segment text to validate
            user_prompt: The original user prompt
            
        Returns:
            bool: True if segment_text is an exact substring of user_prompt
        """
        # Strip whitespace for comparison but check exact match
        segment_text = segment_text.strip()
        if not segment_text:
            return False
            
        # Check if the segment text appears verbatim in the user prompt
        return segment_text in user_prompt
    
    def _parse_segments(self, ai_response: str, reference_code: str, user_prompt: str) -> dict:
        """Parse AI response into structured segments with one-to-one validation"""
        try:
            # JSON schema guarantees valid, clean JSON
            parsed_data = json.loads(ai_response)

            segments = parsed_data.get('segments', [])
            if not segments:
                return {'success': False, 'error': 'No segments found in response', 'segments': [], 'groups': []}

            # Process segments and enforce one-to-one mapping
            valid_segments = []
            valid_groups = []  # EiPL Grader format
            code_lines_list = reference_code.split('\n')
            max_line = len(code_lines_list)
            used_lines = set()  # Track which lines have been assigned

            for segment in segments:
                if not isinstance(segment, dict):
                    continue

                text = segment.get('text', '').strip()
                lines = segment.get('code_lines', [])

                if not text or not lines:
                    continue

                # Validate and filter code lines
                valid_lines = []
                for line in lines:
                    if not isinstance(line, int) or line < 1 or line > max_line:
                        continue

                    # CRITICAL: Check for one-to-one mapping violation
                    if line in used_lines:
                        logger.warning(f"Line {line} already assigned to another segment - skipping to maintain one-to-one mapping")
                        continue

                    valid_lines.append(line)
                    used_lines.add(line)

                # Skip segment if no valid unique lines
                if not valid_lines:
                    logger.warning(f"Segment '{text[:50]}...' has no valid unique lines - skipping")
                    continue

                # Log if segment text is not verbatim (but still use it for conceptual segmentation)
                if not self._validate_segment_is_verbatim(text, user_prompt):
                    logger.info(f"Segment using conceptual text: '{text[:50]}...'")

                # Extract the corresponding code for EiPL format
                code_snippet = '\n'.join(
                    code_lines_list[line-1] for line in sorted(valid_lines)
                    if line-1 < len(code_lines_list)
                )

                # Add to both formats for backward compatibility
                valid_segments.append({
                    'id': len(valid_segments) + 1,
                    'text': text,
                    'code_lines': sorted(valid_lines)
                })

                # EiPL Grader format
                valid_groups.append({
                    'explanation_portion': text,
                    'code': code_snippet
                })

            # Log one-to-one mapping statistics
            total_lines_mapped = len(used_lines)
            logger.info(f"Segmentation complete: {len(valid_segments)} segments mapping {total_lines_mapped} unique lines")

            return {
                'success': True,
                'segments': valid_segments,  # Backward compatibility
                'groups': valid_groups,       # EiPL Grader format
                'error': None
            }

        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'JSON parsing error: {str(e)}', 'segments': [], 'groups': []}
        except Exception as e:
            return {'success': False, 'error': f'Parsing error: {str(e)}', 'segments': [], 'groups': []}
    
    def _determine_comprehension_level(self, segment_count: int, threshold: int = 2, config: dict = None) -> tuple:
        """
        Binary classification based on segment count threshold
        
        Args:
            segment_count: Number of segments identified
            threshold: Threshold for relational vs multi-structural (default: 2)
            config: Problem configuration with custom feedback messages
            
        Returns:
            (level, feedback_message)
        """
        config = config or {}
        custom_feedback = config.get('feedback_messages', {})
        
        if segment_count <= threshold:
            level = 'relational'
            feedback = custom_feedback.get('relational', 
                f'Excellent! Your {segment_count} segment{"s" if segment_count > 1 else ""} shows high-level understanding.')
        else:
            level = 'multi_structural'
            feedback = custom_feedback.get('multi_structural',
                f'Your {segment_count} segments are too detailed. Try to describe the overall purpose in {threshold} or fewer segments.')
        
        return level, feedback

    def _log_segmentation_debug(self, user_prompt: str, reference_code: str, ai_response: str) -> None:
        """Log raw segmentation data for debugging"""
        import os
        from datetime import datetime

        # Create logs directory if it doesn't exist
        log_dir = os.path.join(settings.BASE_DIR, 'logs', 'segmentation')
        os.makedirs(log_dir, exist_ok=True)

        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'segmentation_raw_{timestamp}.json'
        filepath = os.path.join(log_dir, filename)

        # Prepare debug data
        debug_data = {
            'timestamp': timestamp,
            'user_prompt': user_prompt,
            'reference_code': reference_code,
            'ai_raw_response': ai_response,
            'model': self.model_name
        }

        # Write to file
        try:
            with open(filepath, 'w') as f:
                json.dump(debug_data, f, indent=2)
            logger.info(f"Segmentation raw response logged to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to log segmentation debug data: {e}")

    def _log_segmentation_result(self, result: dict, user_prompt: str) -> None:
        """Log final segmentation result for debugging"""
        import os
        from datetime import datetime

        # Create logs directory if it doesn't exist
        log_dir = os.path.join(settings.BASE_DIR, 'logs', 'segmentation')
        os.makedirs(log_dir, exist_ok=True)

        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'segmentation_result_{timestamp}.json'
        filepath = os.path.join(log_dir, filename)

        # Add user prompt to result for context
        result_with_context = {
            'timestamp': timestamp,
            'user_prompt': user_prompt,
            'result': result
        }

        # Write to file
        try:
            with open(filepath, 'w') as f:
                json.dump(result_with_context, f, indent=2)
            logger.info(f"Segmentation result logged to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to log segmentation result: {e}")