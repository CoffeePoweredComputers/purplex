"""AI-powered code generation service."""

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class AITestGenerationService:
    """
    Service for generating test cases using AI.

    Uses the OpenAI Python SDK, which works with any OpenAI-compatible API:
    OpenAI, Meta Llama (via /compat/v1/), Virginia Tech ARC, etc.
    Set OPENAI_BASE_URL to point to your preferred provider.

    Uses synchronous clients for compatibility with gevent workers in production.
    Gevent handles I/O concurrency naturally without requiring async/await.
    """

    def __init__(self):
        self.client = None
        self.model_name = None

        # Mock mode takes priority
        if getattr(settings, "USE_MOCK_OPENAI", False):
            from purplex.problems_app.services.mock_openai import MockOpenAIClient

            self.client = MockOpenAIClient()
            self.model_name = "mock-gpt"
            logger.info("🧪 Using Mock OpenAI provider (USE_MOCK_OPENAI=true)")
            return

        # Initialize OpenAI SDK (works with any OpenAI-compatible API)
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        base_url = getattr(settings, "OPENAI_BASE_URL", None)
        self.model_name = getattr(settings, "GPT_MODEL", "gpt-4o-mini")

        if api_key:
            import openai

            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            self.client = openai.OpenAI(**client_kwargs)
            base_label = f" @ {base_url}" if base_url else ""
            logger.info(f"✅ AI provider ready (model: {self.model_name}{base_label})")
        else:
            logger.warning("⚠️  OPENAI_API_KEY not configured — AI features disabled")

    def _call_ai(self, messages, max_tokens=2000, temperature=0):
        """
        Synchronous AI call via OpenAI SDK.
        Uses sync client for compatibility with gevent workers.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = response.choices[0].message.content
            logger.info(f"🤖 AI call successful (model: {self.model_name})")
            return content

        except Exception as e:
            logger.error(f"❌ AI call failed: {str(e)}")
            raise

    def _generate_eipl_variations(self, problem, user_prompt: str) -> dict[str, Any]:
        """
        Generate code variations for EiPL problems.
        Uses synchronous client - gevent handles I/O concurrency automatically.
        """
        if not self.client:
            return {
                "success": False,
                "error": "No AI provider configured (set OPENAI_API_KEY)",
                "variations": [],
                "model": None,
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

            # Build messages for AI API call
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # In mock mode, inject the reference solution so the mock can
            # return code that actually passes Docker test execution
            if getattr(settings, "USE_MOCK_OPENAI", False):
                messages.append(
                    {
                        "role": "developer",
                        "name": "mock_context",
                        "content": problem.reference_solution,
                    }
                )

            # Make synchronous API call - gevent yields during I/O automatically
            # Use 4000 tokens to allow complex algorithms (~40 lines per variation)
            content = self._call_ai(messages=messages, max_tokens=4000, temperature=0)

            # Extract code blocks
            import re

            code_blocks = re.findall(r"```python\n(.*?)\n```", content, re.DOTALL)

            # If no code blocks found, try splitting by function definitions
            if not code_blocks:
                # Split by 'def' and reconstruct
                parts = content.split("def ")
                code_blocks = []
                for part in parts[1:]:  # Skip first empty part
                    code_blocks.append("def " + part.strip())

            # Validate that we have the expected function name
            valid_variations = []
            for code in code_blocks:
                if f"def {problem.function_name}" in code:
                    valid_variations.append(code.strip())

            # Require exactly 5 variations for a successful generation
            if len(valid_variations) < 5:
                logger.warning(
                    f"Insufficient variations generated: {len(valid_variations)}/5. "
                    f"User prompt length: {len(user_prompt)} chars"
                )
                return {
                    "success": False,
                    "error": (
                        f"Could not generate enough code variations from your description "
                        f"({len(valid_variations)}/5 generated). Please try again with a more "
                        "detailed explanation of the code's behavior."
                    ),
                    "variations": valid_variations,
                    "model": self.model_name,
                }

            return {
                "success": True,
                "variations": valid_variations[:5],
                "error": None,
                "model": self.model_name,
            }

        except Exception as e:
            logger.error(f"Failed to generate EIPL variations: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "variations": [],
                "model": self.model_name,
            }

    def generate_eipl_variations(self, problem, user_prompt: str) -> dict[str, Any]:
        """
        Public entry point for EiPL variation generation.

        Directly calls the synchronous implementation - no event loop complexity needed.
        Works seamlessly with both gevent (production) and prefork (development) workers.
        Gevent automatically handles I/O concurrency via monkey patching.
        """
        return self._generate_eipl_variations(problem, user_prompt)
