"""AI-powered code generation service."""
import logging
from typing import Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class AITestGenerationService:
    """Service for generating test cases using AI."""
    
    def __init__(self):
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.model_name = getattr(settings, 'GPT_MODEL', 'gpt-4o-mini')
        if self.openai_api_key:
            import openai
            self.client = openai.OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            
    def generate_eipl_variations(self, problem, user_prompt: str) -> Dict[str, Any]:
        """Generate code variations for EiPL problems based on user's description"""
        if not self.client:
            return {
                'success': False,
                'error': 'OpenAI API key not configured',
                'variations': []
            }
        
        try:
            # Create a system prompt specific to the problem
            system_prompt = f"""
Create five different implementations of a function called {problem.function_name} based on the user's description.
The function should match this problem:

Guidelines:
1. Each implementation MUST be different 
2. Make the code beginner-friendly and avoid unnecessary built-in functions
3. Each function MUST be named exactly: {problem.function_name}. If it is not the grading mechanism will fail.
4. Return only the function implementations, no additional text or comments

Format your response as:
```python
def {problem.function_name}(...):
    # implementation 1
```
```python
def {problem.function_name}(...):
    # implementation 2
```
```python
def {problem.function_name}(...):
    # implementation 3
```
```python
def {problem.function_name}(...):
    # implementation 4
```
```python
def {problem.function_name}(...):
    # implementation 5
```
"""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Extract code blocks
            import re
            code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
            
            # If no code blocks found, try splitting by function definitions
            if not code_blocks:
                # Split by 'def' and reconstruct
                parts = content.split('def ')
                code_blocks = []
                for part in parts[1:]:  # Skip first empty part
                    code_blocks.append('def ' + part.strip())
            
            # Validate that we have the expected function name
            valid_variations = []
            for code in code_blocks:
                if f"def {problem.function_name}" in code:
                    valid_variations.append(code.strip())
            
            return {
                'success': True,
                'variations': valid_variations[:5],  # Return up to 5 variations
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Failed to generate EIPL variations: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'variations': []
            }