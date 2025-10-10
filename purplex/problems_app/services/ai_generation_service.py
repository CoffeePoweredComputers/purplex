"""AI-powered code generation service with async support."""
import logging
import asyncio
from typing import Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class AITestGenerationService:
    """Service for generating test cases using AI with async support."""

    def __init__(self):
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.model_name = getattr(settings, 'GPT_MODEL', 'gpt-4o-mini')
        if self.openai_api_key:
            import openai
            # Initialize both sync and async clients
            self.client = openai.OpenAI(api_key=self.openai_api_key)
            self.async_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            self.async_client = None
            
    async def _generate_eipl_variations_async(self, problem, user_prompt: str) -> Dict[str, Any]:
        """
        ASYNC version: Generate code variations for EiPL problems.
        PERFORMANCE: Async I/O allows other tasks to run during OpenAI API wait.
        """
        if not self.async_client:
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

            # Build parameters dict to handle different API versions
            api_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0  # All modern models support temperature parameter
            }

            # PERFORMANCE: Async API call allows Celery to handle other tasks while waiting
            try:
                # Try with the traditional parameter first
                response = await self.async_client.chat.completions.create(
                    **api_params,
                    max_tokens=2000
                )
            except Exception as e:
                error_str = str(e)
                # If OpenAI says to use max_completion_tokens, use it
                if "max_completion_tokens" in error_str or "'max_tokens' is not supported" in error_str:
                    response = await self.async_client.chat.completions.create(
                        **api_params,
                        max_completion_tokens=2000
                    )
                else:
                    raise

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

    def generate_eipl_variations(self, problem, user_prompt: str) -> Dict[str, Any]:
        """
        Synchronous wrapper around async generation for backward compatibility.
        PERFORMANCE: Uses asyncio.run() to execute async code in sync context.
        """
        try:
            # Run the async function in a new event loop
            return asyncio.run(self._generate_eipl_variations_async(problem, user_prompt))
        except Exception as e:
            logger.error(f"Failed to run async EIPL generation: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'variations': []
            }
