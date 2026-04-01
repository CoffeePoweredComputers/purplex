"""
Mock OpenAI client for development and testing.

Provides a drop-in replacement for openai.OpenAI() that returns
deterministic responses without requiring an API key or network access.

Used by AITestGenerationService and SegmentationService when
USE_MOCK_OPENAI=true. Follows the MockFirebaseAuth pattern from
purplex/users_app/mock_firebase.py.

Safety: Cannot activate in production — blocked by two independent guards:
  1. config.use_mock_openai property returns False for non-dev envs
  2. MockOpenAIClient.__init__ raises RuntimeError if PURPLEX_ENV=production
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)


class _MockMessage:
    """Mimics openai.types.chat.ChatCompletionMessage."""

    def __init__(self, content: str):
        self.content = content
        self.role = "assistant"


class _MockChoice:
    """Mimics openai.types.chat.Choice."""

    def __init__(self, content: str):
        self.message = _MockMessage(content)
        self.index = 0
        self.finish_reason = "stop"


class _MockCompletion:
    """Mimics openai.types.chat.ChatCompletion."""

    def __init__(self, content: str):
        self.choices = [_MockChoice(content)]
        self.model = "mock-gpt"
        self.id = "mock-completion"
        self.usage = None


class _MockCompletions:
    """Mimics openai.resources.chat.Completions."""

    def create(self, *, model, messages, **kwargs):
        """Route to the appropriate mock response based on system prompt content."""
        system_content = ""
        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg.get("content", "")
                break

        if "Create five different implementations" in system_content:
            content = self._variation_response(messages, system_content)
        elif "ONE-TO-ONE MAPPING RULES" in system_content:
            content = self._segmentation_response(messages, system_content)
        else:
            content = "Mock response: unrecognized call pattern"

        logger.info(f"[MockOpenAI] Generated response for model={model}")
        return _MockCompletion(content)

    def _variation_response(self, messages, system_content) -> str:
        """Return 5 code variations using the reference solution.

        The reference solution is injected as a developer/mock_context message
        by _generate_eipl_variations when mock mode is active.
        """
        reference_solution = None
        for msg in messages:
            if msg.get("role") == "developer" and msg.get("name") == "mock_context":
                reference_solution = msg.get("content", "")

        # Extract function name from system prompt
        match = re.search(r"function called (\w+)", system_content)
        func_name = match.group(1) if match else "unknown"

        if reference_solution:
            code = reference_solution.strip()
        else:
            code = f"def {func_name}(*args, **kwargs):\n    pass"

        blocks = []
        for i in range(5):
            comment = f"# variation {i + 1}\n" if i > 0 else ""
            blocks.append(f"```python\n{comment}{code}\n```")
        return "\n\n".join(blocks)

    def _segmentation_response(self, messages, system_content) -> str:
        """Return a 2-segment JSON response (relational comprehension level).

        Parses reference code line count from the system prompt to produce
        valid code_lines mappings.
        """
        code_match = re.search(r"```python\n(.*?)\n```", system_content, re.DOTALL)
        num_lines = len(code_match.group(1).strip().split("\n")) if code_match else 3

        user_text = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_text = msg.get("content", "")
                break

        mid = max(1, num_lines // 2)
        return json.dumps(
            {
                "segments": [
                    {
                        "id": 1,
                        "text": user_text[: len(user_text) // 2] or "function setup",
                        "code_lines": list(range(1, mid + 1)),
                    },
                    {
                        "id": 2,
                        "text": user_text[len(user_text) // 2 :] or "computation",
                        "code_lines": list(range(mid + 1, num_lines + 1))
                        or [num_lines],
                    },
                ]
            }
        )


class _MockChat:
    """Mimics openai.resources.Chat."""

    def __init__(self):
        self.completions = _MockCompletions()


class MockOpenAIClient:
    """Drop-in replacement for openai.OpenAI().

    Implements the interface subset used by AITestGenerationService and
    SegmentationService: client.chat.completions.create().
    """

    def __init__(self, api_key=None):
        if os.environ.get("PURPLEX_ENV") == "production":
            raise RuntimeError("MockOpenAIClient cannot be used in production")
        self.chat = _MockChat()
        self.api_key = api_key or "mock-api-key"
        logger.info("[MockOpenAI] Initialized mock OpenAI client")
