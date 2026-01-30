import json
import os
from collections import defaultdict
from typing import Any

import openai
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_not_exception_type,
)

from rlm.clients.base_lm import BaseLM
from rlm.core.types import ModelUsageSummary, UsageSummary

load_dotenv()

# Load API keys from environment variables
DEFAULT_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_VERCEL_API_KEY = os.getenv("AI_GATEWAY_API_KEY")
DEFAULT_PRIME_INTELLECT_BASE_URL = "https://api.pinference.ai/api/v1/"


class OpenAIClient(BaseLM):
    """
    LM Client for running models with the OpenAI API. Works with vLLM as well.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ):
        super().__init__(model_name=model_name, **kwargs)

        if api_key is None:
            if base_url == "https://api.openai.com/v1" or base_url is None:
                api_key = DEFAULT_OPENAI_API_KEY
            elif base_url == "https://openrouter.ai/api/v1":
                api_key = DEFAULT_OPENROUTER_API_KEY
            elif base_url == "https://ai-gateway.vercel.sh/v1":
                api_key = DEFAULT_VERCEL_API_KEY

        # For vLLM, set base_url to local vLLM server address.
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

        # Per-model usage tracking
        self.model_call_counts: dict[str, int] = defaultdict(int)
        self.model_input_tokens: dict[str, int] = defaultdict(int)
        self.model_output_tokens: dict[str, int] = defaultdict(int)
        self.model_total_tokens: dict[str, int] = defaultdict(int)

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_not_exception_type(
            (
                openai.BadRequestError,
                openai.AuthenticationError,
                openai.NotFoundError,
            )
        ),
    )
    def _create_completion(self, **kwargs):
        return self.client.chat.completions.create(**kwargs)

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_not_exception_type(
            (
                openai.BadRequestError,
                openai.AuthenticationError,
                openai.NotFoundError,
            )
        ),
    )
    async def _create_acompletion(self, **kwargs):
        return await self.async_client.chat.completions.create(**kwargs)

    def completion(
        self,
        prompt: str | list[dict[str, Any]],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list) and all(isinstance(item, dict) for item in prompt):
            messages = prompt
        else:
            raise ValueError(f"Invalid prompt type: {type(prompt)}")

        model = model or self.model_name
        if not model:
            raise ValueError("Model name is required for OpenAI client.")

        extra_body = {}
        if self.client.base_url == DEFAULT_PRIME_INTELLECT_BASE_URL:
            extra_body["usage"] = {"include": True}

        kwargs = {"model": model, "messages": messages, "extra_body": extra_body}
        if tools is not None:
            kwargs["tools"] = tools

        # Merge kwargs from __init__
        kwargs.update(self.kwargs)

        # Handle max_tokens vs max_completion_tokens
        if model and (model.startswith("o1") or model.startswith("o3")):
            # Rename max_tokens to max_completion_tokens if present
            if "max_tokens" in kwargs:
                if "max_completion_tokens" not in kwargs:
                    kwargs["max_completion_tokens"] = kwargs["max_tokens"]
                del kwargs["max_tokens"]
            
            # Set default if still missing
            if "max_completion_tokens" not in kwargs:
                kwargs["max_completion_tokens"] = 8192
        else:
            # Default for standard models
            if "max_tokens" not in kwargs and "max_completion_tokens" not in kwargs:
                kwargs["max_completion_tokens"] = 8192

        response = self._create_completion(**kwargs)
        self._track_cost(response, model)
        
        message = response.choices[0].message
        content = message.content

        if content is None and message.tool_calls:
            code_lines = []
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                
                # Construct python call
                args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                code_lines.append(f"print({func_name}({args_str}))")
            
            # Wrap in REPL block
            return "```repl\n" + "\n".join(code_lines) + "\n```"

        return content or ""

    async def acompletion(
        self,
        prompt: str | list[dict[str, Any]],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list) and all(isinstance(item, dict) for item in prompt):
            messages = prompt
        else:
            raise ValueError(f"Invalid prompt type: {type(prompt)}")

        model = model or self.model_name
        if not model:
            raise ValueError("Model name is required for OpenAI client.")

        extra_body = {}
        if self.client.base_url == DEFAULT_PRIME_INTELLECT_BASE_URL:
            extra_body["usage"] = {"include": True}

        kwargs = {"model": model, "messages": messages, "extra_body": extra_body}
        if tools is not None:
            kwargs["tools"] = tools

        # Merge kwargs from __init__
        kwargs.update(self.kwargs)

        # Handle max_tokens vs max_completion_tokens
        if model and (model.startswith("o1") or model.startswith("o3")):
            # Rename max_tokens to max_completion_tokens if present
            if "max_tokens" in kwargs:
                if "max_completion_tokens" not in kwargs:
                    kwargs["max_completion_tokens"] = kwargs["max_tokens"]
                del kwargs["max_completion_tokens"]
            
            # Set default if still missing
            if "max_completion_tokens" not in kwargs:
                kwargs["max_completion_tokens"] = 8192
        else:
            # Default for standard models
            if "max_tokens" not in kwargs and "max_completion_tokens" not in kwargs:
                kwargs["max_completion_tokens"] = 8192

        response = await self._create_acompletion(**kwargs)
        self._track_cost(response, model)
        
        message = response.choices[0].message
        content = message.content

        if content is None and message.tool_calls:
            code_lines = []
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                
                # Construct python call
                args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                code_lines.append(f"print({func_name}({args_str}))")
            
            # Wrap in REPL block
            return "```repl\n" + "\n".join(code_lines) + "\n```"

        return content or ""

    def _track_cost(self, response: openai.ChatCompletion, model: str):
        self.model_call_counts[model] += 1

        usage = getattr(response, "usage", None)
        if usage is None:
            raise ValueError("No usage data received. Tracking tokens not possible.")

        self.model_input_tokens[model] += usage.prompt_tokens
        self.model_output_tokens[model] += usage.completion_tokens
        self.model_total_tokens[model] += usage.total_tokens

        # Track last call for handler to read
        self.last_prompt_tokens = usage.prompt_tokens
        self.last_completion_tokens = usage.completion_tokens

    def get_usage_summary(self) -> UsageSummary:
        model_summaries = {}
        for model in self.model_call_counts:
            model_summaries[model] = ModelUsageSummary(
                total_calls=self.model_call_counts[model],
                total_input_tokens=self.model_input_tokens[model],
                total_output_tokens=self.model_output_tokens[model],
            )
        return UsageSummary(model_usage_summaries=model_summaries)

    def get_last_usage(self) -> ModelUsageSummary:
        return ModelUsageSummary(
            total_calls=1,
            total_input_tokens=self.last_prompt_tokens,
            total_output_tokens=self.last_completion_tokens,
        )
