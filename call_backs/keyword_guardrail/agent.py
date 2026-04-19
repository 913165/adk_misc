from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai import types
from typing import Optional


# ── 1. Define forbidden keywords ────────────────────────────────────
FORBIDDEN_KEYWORDS = [
    "hack",
    "exploit",
    "password",
    "malware",
    "virus",
    "crack",
]


# ── 2. Define the guardrail callback ────────────────────────────────
def keyword_guardrail(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    A before_model callback that scans the user's message for
    forbidden keywords. If found, it blocks the LLM call entirely
    and returns a safe hardcoded response instead.

    Returns:
        LlmResponse  → if a forbidden keyword is found (LLM call skipped)
        None         → if clean (LLM call proceeds normally)
    """

    print(f"[Guardrail] Checking request for agent: '{callback_context.agent_name}'")

    # ── Extract the last user message ──────────────────────────────
    last_user_message = ""
    if llm_request.contents:
        for content in reversed(llm_request.contents):
            if content.role == "user" and content.parts:
                last_user_message = content.parts[0].text or ""
                break

    print(f"[Guardrail] User message: '{last_user_message}'")

    # ── Scan for forbidden keywords ─────────────────────────────────
    message_lower = last_user_message.lower()
    detected = [kw for kw in FORBIDDEN_KEYWORDS if kw in message_lower]

    if detected:
        # ── BLOCK — return response without calling LLM ─────────────
        print(f"[Guardrail] 🚫 BLOCKED — forbidden keywords detected: {detected}")
        blocked_message = (
            f"I'm sorry, I can't help with that request. "
            f"The following topic(s) are not allowed: {', '.join(detected)}."
        )
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=blocked_message)]
            )
        )

    # ── ALLOW — no forbidden keywords found ────────────────────────
    print(f"[Guardrail] ✅ ALLOWED — request is clean, proceeding to LLM.")
    return None  # LLM call proceeds normally


# ── 3. root_agent ───────────────────────────────────────────────────
root_agent = LlmAgent(
    name="KeywordGuardrailAgent",
    model="gemini-3.1-pro-preview",
    instruction="You are a helpful assistant.",
    before_model_callback=keyword_guardrail
)