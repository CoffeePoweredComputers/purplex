"""Segmentation service for prompt analysis."""
import time
import re
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SegmentationService:
    """Service for prompt segmentation analysis using GPT-4"""
    
    def __init__(self):
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.model_name = getattr(settings, 'GPT_MODEL', 'gpt-4o-mini')
        if self.openai_api_key:
            import openai
            self.client = openai.OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
    
    def segment_prompt(self, user_prompt: str, reference_code: str, problem_config: dict = None) -> dict:
        """
        Segment user prompt and map to code lines using GPT-4
        
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
                'error': 'OpenAI API key not configured',
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
            
            # Make API call to GPT-4
            response = self.client.chat.completions.create(
                model=self.model_name,  # Using configured model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Please analyze this prompt: {user_prompt}"}
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            
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
            
            return {
                'success': True,
                'segments': segments,
                'groups': groups,  # Include EiPL Grader format
                'segment_count': segment_count,
                'comprehension_level': level,
                'feedback': feedback,
                'processing_time': time.time() - start_time,
                'error': None
            }
            
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
        """Build few-shot prompt with examples for consistent segmentation using verbatim text extraction"""
        
        # Start with base prompt
        prompt_parts = ["""# Task: 
Map EXACT portions of the student's explanation to corresponding code sections.

# CRITICAL RULES:
1. You MUST use ONLY the EXACT text from the student's explanation
2. Each segment text MUST be a character-for-character substring from the student's response
3. DO NOT paraphrase, summarize, or create ANY new text
4. DO NOT add words, remove words, or change punctuation
5. Copy text VERBATIM - exactly as written by the student

# How to Segment:
1. Identify distinct concepts/steps in the student's explanation
2. Extract the EXACT text for each concept (copy-paste from their response)
3. Match each exact text portion to its corresponding code lines
4. One explanation portion can map to multiple code lines
5. Not all explanation text needs to be used
6. Not all code needs to be mapped

# Two Approaches:
1. Multistructural: If explanation describes steps/implementation details, split into smallest meaningful exact phrases
2. Relational: If explanation describes overall functionality, use the complete exact description

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
# WARNING:
Every segment "text" field must be an EXACT substring of the student's response.
If you create new text, the segmentation is invalid.

INSTRUCTIONS:
- Extract EXACT text portions from the student's explanation (no paraphrasing!)
- Each segment text MUST appear verbatim in the student's response
- Map segments to code lines (1-indexed)
- Return your analysis as JSON in this exact format:

{
    "segments": [
        {"id": 1, "text": "EXACT text from student response", "code_lines": [1, 2, 3]},
        {"id": 2, "text": "another EXACT text portion", "code_lines": [4, 5]}
    ]
}

REMEMBER: Copy-paste precision required - every character in "text" must be found in the student's original response.""")
        
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
        """Parse AI response into structured segments with verbatim validation"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if not json_match:
                return {'success': False, 'error': 'No JSON found in response', 'segments': [], 'groups': []}
            
            json_str = json_match.group(0)
            parsed_data = json.loads(json_str)
            
            segments = parsed_data.get('segments', [])
            if not segments:
                return {'success': False, 'error': 'No segments found in response', 'segments': [], 'groups': []}
            
            # Process segments without filtering
            valid_segments = []
            valid_groups = []  # EiPL Grader format
            code_lines_list = reference_code.split('\n')
            max_line = len(code_lines_list)
            
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                    
                text = segment.get('text', '').strip()
                lines = segment.get('code_lines', [])
                
                if not text or not lines:
                    continue
                
                # Log warning if segment text is not verbatim from user prompt (but keep it)
                if not self._validate_segment_is_verbatim(text, user_prompt):
                    logger.warning(f"Segment not verbatim from user prompt: '{text[:50]}...'")
                    # Note: We still keep the segment for pure segmentation
                
                # Validate and clamp code lines
                valid_lines = [line for line in lines if isinstance(line, int) and 1 <= line <= max_line]
                if not valid_lines:
                    valid_lines = [1]  # Default to first line if no valid lines
                
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