"""AI-powered code generation service."""

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


def _variation_system_prompt(function_name: str, count: int) -> str:
    """Build the system prompt asking the LLM for ``count`` implementations.

    The mock LLM (``mock_openai.py``) recognises this prompt by its
    ``implementation(s) of a function called`` wording and returns one version
    per ``# implementation`` stub, so keep the two in step. For ``count=5``
    the text is the original EiPL prompt, unchanged.
    """
    if count < 1:
        raise ValueError(f"count must be at least 1, got {count}")
    number = _NUMBER_WORDS.get(count, str(count))
    if count == 1:
        request = (
            f"Create exactly one implementation of a function called {function_name}"
        )
        guidelines = [
            "Make the code beginner-friendly and avoid unnecessary built-in functions",
            f"The function MUST be named exactly: {function_name}. If it is not the grading mechanism will fail.",
            "Return only the function implementation, no additional text or comments",
        ]
    else:
        request = f"Create {number} different implementations of a function called {function_name}"
        guidelines = [
            "Each implementation MUST be different",
            "Make the code beginner-friendly and avoid unnecessary built-in functions",
            f"Each function MUST be named exactly: {function_name}. If it is not the grading mechanism will fail.",
            "Return only the function implementations, no additional text or comments",
        ]
    numbered = "\n".join(f"{i}. {g}" for i, g in enumerate(guidelines, start=1))
    labels = (
        ["implementation"]
        if count == 1
        else [f"implementation {i}" for i in range(1, count + 1)]
    )
    stubs = "".join(
        f"```python\ndef {function_name}(...):\n    # {label}\n```\n"
        for label in labels
    )
    return (
        f"\n{request} based on the user's description.\n"
        "The function should match this problem:\n\n"
        f"Guidelines:\n{numbered}\n\n"
        f"Format your response as:\n{stubs}"
    )


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

    def _generate_eipl_variations(
        self, problem, user_prompt: str, count: int = 5
    ) -> dict[str, Any]:
        """
        Generate ``count`` code versions of the user's description.
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
            system_prompt = _variation_system_prompt(problem.function_name, count)

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

            # Require exactly ``count`` variations for a successful generation
            if len(valid_variations) < count:
                logger.warning(
                    f"Insufficient variations generated: {len(valid_variations)}/{count}. "
                    f"User prompt length: {len(user_prompt)} chars"
                )
                return {
                    "success": False,
                    "error": (
                        f"Could not generate enough code variations from your description "
                        f"({len(valid_variations)}/{count} generated). Please try again with a more "
                        "detailed explanation of the code's behavior."
                    ),
                    "variations": valid_variations,
                    "model": self.model_name,
                }

            return {
                "success": True,
                "variations": valid_variations[:count],
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

    def generate_eipl_variations(
        self, problem, user_prompt: str, count: int = 5
    ) -> dict[str, Any]:
        """
        Public entry point for EiPL variation generation.

        Directly calls the synchronous implementation - no event loop complexity needed.
        Works seamlessly with both gevent (production) and prefork (development) workers.
        Gevent automatically handles I/O concurrency via monkey patching.
        """
        return self._generate_eipl_variations(problem, user_prompt, count)
