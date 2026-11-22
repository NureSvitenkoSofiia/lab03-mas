"""Підмінні LLM-моделі для офлайн-тестів без витрат квоти Gemini API."""

from __future__ import annotations

import threading
from collections.abc import AsyncGenerator

from google.adk.models import LlmRequest, LlmResponse
from google.adk.models.base_llm import BaseLlm
from google.genai import types
from pydantic import Field, PrivateAttr


class ScriptedLlm(BaseLlm):
    """Потокобезпечна підмінна модель, яка розрізняє агентів за ROLE: маркером."""

    script: dict[str, list[str]] = Field(default_factory=dict)
    calls: list[str] = Field(default_factory=list)
    tool_calls: dict[str, list[tuple[str, dict]]] = Field(default_factory=dict)
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)

    def _detect_role(self, sys_inst: str) -> str:
        for role_key in self.script:
            if role_key in sys_inst:
                return role_key
        for role_key in self.tool_calls:
            if role_key in sys_inst:
                return role_key
        return "default"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        sys_inst = ""
        if llm_request.config and llm_request.config.system_instruction:
            sys_inst = str(llm_request.config.system_instruction)

        with self._lock:
            role = self._detect_role(sys_inst)
            self.calls.append(role)

            last_part = (
                llm_request.contents[-1].parts[0]
                if llm_request.contents and llm_request.contents[-1].parts
                else None
            )
            if (
                role in self.tool_calls
                and self.tool_calls[role]
                and not (last_part and last_part.function_response)
            ):
                fn_name, fn_args = self.tool_calls[role].pop(0)
                part = types.Part(
                    function_call=types.FunctionCall(name=fn_name, args=fn_args)
                )
            else:
                responses = self.script.get(role, ["{}"])
                payload = responses.pop(0) if len(responses) > 1 else responses[0]
                part = types.Part(text=payload)

        yield LlmResponse(content=types.Content(role="model", parts=[part]))
