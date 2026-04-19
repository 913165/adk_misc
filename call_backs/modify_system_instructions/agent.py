from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai import types
from typing import Optional


# ── 1. Define the callback ──────────────────────────────────────────
def modify_system_instruction(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:

    print(f"[Callback] Modifying system instruction for: '{callback_context.agent_name}'")

    prefix = "[IMPORTANT: Always respond in bullet points.] "
    original = llm_request.config.system_instruction

    # ── Handle all three possible types ────────────────────────────

    if original is None:
        # No instruction set at all — create one from scratch
        llm_request.config.system_instruction = types.Content(
            role="system",
            parts=[types.Part(text=prefix)]
        )
        print(f"[Callback] No instruction found — injected: '{prefix}'")

    elif isinstance(original, str):
        # adk web passes instruction as a plain string — wrap it
        modified_text = prefix + original
        llm_request.config.system_instruction = types.Content(
            role="system",
            parts=[types.Part(text=modified_text)]
        )
        print(f"[Callback] Original (str) : '{original}'")
        print(f"[Callback] Modified       : '{modified_text}'")

    elif isinstance(original, types.Content):
        # Already a Content object — modify the first part directly
        if original.parts:
            existing_text = original.parts[0].text or ""
            modified_text = prefix + existing_text
            original.parts[0].text = modified_text
            print(f"[Callback] Original (Content) : '{existing_text}'")
            print(f"[Callback] Modified           : '{modified_text}'")
        else:
            original.parts = [types.Part(text=prefix)]
            print(f"[Callback] Empty Content — injected: '{prefix}'")

    else:
        print(f"[Callback] Unknown instruction type: {type(original)} — skipping")

    return None  # Let the modified request proceed to LLM


# ── 2. root_agent ───────────────────────────────────────────────────
root_agent = LlmAgent(
    name="ModifyInstructionAgent",
    model="gemini-3.1-pro-preview",
    instruction="You are a helpful assistant.",
    before_model_callback=modify_system_instruction
)