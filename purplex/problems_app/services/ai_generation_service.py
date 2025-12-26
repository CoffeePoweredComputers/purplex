"""AI-powered code generation service."""

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class AITestGenerationService:
    """
    Service for generating test cases using AI.

    Supports both Llama and OpenAI providers via configuration.
    Provider is selected via AI_PROVIDER setting ('llama' or 'openai').
    Fails immediately if the configured provider is unavailable - no fallback.

    Uses synchronous clients for compatibility with gevent workers in production.
    Gevent handles I/O concurrency naturally without requiring async/await.
    """

    def __init__(self):
        # Determine which provider to use
        self.provider = getattr(settings, "AI_PROVIDER", "openai").lower()

        # Initialize OpenAI (sync client only)
        self.openai_api_key = getattr(settings, "OPENAI_API_KEY", None)
        self.openai_model = getattr(settings, "GPT_MODEL", "gpt-4o-mini")
        if self.openai_api_key:
            import openai

            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        else:
            self.openai_client = None

        # Initialize Llama (sync client only)
        self.llama_api_key = getattr(settings, "LLAMA_API_KEY", None)
        self.llama_model = getattr(
            settings, "LLAMA_MODEL", "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
        )
        if self.llama_api_key:
            try:
                from llama_api_client import LlamaAPIClient

                self.llama_client = LlamaAPIClient(api_key=self.llama_api_key)
            except ImportError:
                logger.warning(
                    "llama-api-client not installed, Llama provider unavailable"
                )
                self.llama_client = None
        else:
            self.llama_client = None

        # Select active client based on provider setting
        self._select_clients()

    def _select_clients(self):
        """Select which client to use based on configuration"""
        if self.provider == "llama" and self.llama_client:
            self.client = self.llama_client
            self.model_name = self.llama_model
            logger.info(f"✅ Using Llama API provider (model: {self.llama_model})")
        elif self.provider == "openai" and self.openai_client:
            self.client = self.openai_client
            self.model_name = self.openai_model
            logger.info(f"✅ Using OpenAI API provider (model: {self.openai_model})")
        else:
            # Fallback or no provider available
            self.client = None
            self.model_name = None
            logger.warning(
                f"⚠️  No valid AI provider configured (provider={self.provider})"
            )

    def _call_ai(self, messages, max_tokens=2000, temperature=0):
        """
        Unified synchronous AI call that handles both Llama and OpenAI APIs.
        Raises exception immediately on failure - no fallback.

        Uses sync clients for compatibility with gevent workers.
        Gevent automatically handles I/O concurrency via monkey patching.
        """
        try:
            if self.provider == "llama":
                # Llama API call (max_tokens not supported in llama-api-client 0.1.0)
                response = self.client.chat.completions.create(
                    model=self.model_name, messages=messages, temperature=temperature
                )
                content = response.completion_message.content.text
                logger.info(f"🦙 Llama API call successful (model: {self.model_name})")

            else:  # openai
                # OpenAI API call with fallback for max_tokens parameter
                try:
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                except TypeError as e:
                    # If max_tokens is not accepted, try max_completion_tokens
                    if "max_tokens" in str(e):
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages,
                            max_completion_tokens=max_tokens,
                            temperature=temperature,
                        )
                    else:
                        raise

                content = response.choices[0].message.content
                logger.info(f"🤖 OpenAI API call successful (model: {self.model_name})")

            return content

        except Exception as e:
            logger.error(f"❌ {self.provider.upper()} API call failed: {str(e)}")
            raise  # Fail immediately - no fallback

    def _generate_eipl_variations(self, problem, user_prompt: str) -> dict[str, Any]:
        """
        Generate code variations for EiPL problems.
        Uses synchronous client - gevent handles I/O concurrency automatically.
        Supports both Llama and OpenAI providers.
        """
        if not self.client:
            return {
                "success": False,
                "error": f"No AI provider configured (provider={self.provider})",
                "variations": [],
                "model": None,
                "provider": self.provider,
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

            # Make synchronous API call - gevent yields during I/O automatically
            content = self._call_ai(messages=messages, max_tokens=2000, temperature=0)

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

            return {
                "success": True,
                "variations": valid_variations[:5],  # Return up to 5 variations
                "error": None,
                "model": self.model_name,
                "provider": self.provider,
            }

        except Exception as e:
            logger.error(f"Failed to generate EIPL variations: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "variations": [],
                "model": self.model_name,
                "provider": self.provider,
            }

    def generate_eipl_variations(self, problem, user_prompt: str) -> dict[str, Any]:
        """
        Public entry point for EiPL variation generation.

        Directly calls the synchronous implementation - no event loop complexity needed.
        Works seamlessly with both gevent (production) and prefork (development) workers.
        Gevent automatically handles I/O concurrency via monkey patching.
        """
        return self._generate_eipl_variations(problem, user_prompt)
