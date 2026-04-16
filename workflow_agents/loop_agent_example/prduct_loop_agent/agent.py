from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.tool_context import ToolContext

# --- Constants ---
GEMINI_MODEL = "gemini-2.5-flash"


# ======================================================================
# EXIT-LOOP TOOL
# The QA agent calls this when the listing passes. Setting
# tool_context.actions.escalate = True tells the LoopAgent to stop.
# ======================================================================

def exit_loop(tool_context: ToolContext) -> dict:
    """Call this function ONLY when the product listing has been APPROVED
    and meets all quality standards. This will exit the refinement loop.
    """
    print(f"\n  [exit_loop called by {tool_context.agent_name} — listing approved, stopping loop]\n")
    tool_context.actions.escalate = True
    return {"status": "loop_exited", "message": "Listing approved. Loop terminated."}


# ======================================================================
# LOOP AGENT — E-Commerce Product Description Generator
#
# Flow:  Write/Rewrite → QA Audit → (if score >= 78, call exit_loop)
# ======================================================================


# --- Stage 1: Product Description Writer ---
product_writer_agent = LlmAgent(
    name="ProductWriterAgent",
    model=GEMINI_MODEL,
    instruction="""
    You are a senior e-commerce copywriter for a premium electronics brand.

    **Product Details (from catalog):**
    The user message contains raw product specs. Use them as your source of truth.

    **Previous QA Feedback (if any):**
    {qa_feedback?}

    If QA feedback is provided above, carefully rewrite the listing to fix
    every issue mentioned. Do NOT ignore any feedback point.

    If no QA feedback exists, write a fresh product listing following these rules:

    **Brand Voice Guidelines:**
    - Tone: Confident, modern, conversational — not robotic or salesy
    - Never use ALL CAPS for emphasis (use italics sparingly instead)
    - Never use exclamation marks
    - Avoid clichés like "game-changer", "revolutionary", "best-in-class"

    **Listing Structure (follow exactly):**
    1. **Title** — Brand + Product Name + Key Differentiator (under 80 chars)
    2. **Tagline** — One punchy sentence (under 15 words)
    3. **Description** — 3 short paragraphs (2-3 sentences each):
       - Para 1: What it is and who it's for
       - Para 2: Standout feature with a real-world benefit
       - Para 3: Build quality, warranty, or trust signal
    4. **Key Features** — Exactly 5 bullet points, each under 12 words
    5. **SEO Keywords** — 5 comma-separated search terms customers would type

    Output the complete listing in markdown format.
    """,
    description="Writes or rewrites a product description based on QA feedback.",
    output_key="product_listing",
)


# --- Stage 2: QA Auditor (with exit_loop tool) ---
qa_auditor_agent = LlmAgent(
    name="QAAuditorAgent",
    model=GEMINI_MODEL,
    instruction="""
    You are a strict Quality Assurance editor for an e-commerce brand.

    **Product Listing to Audit:**
    {product_listing}

    **Audit Checklist (score each criterion 0-10):**

    1. **Title Quality** — Under 80 chars? Includes brand + product + differentiator?
    2. **Tagline** — Present? Under 15 words? Punchy and memorable?
    3. **Description Structure** — Exactly 3 paragraphs? Each 2-3 sentences?
    4. **Tone Compliance** — No ALL CAPS, no exclamation marks, no clichés
       ("game-changer", "revolutionary", "best-in-class", "cutting-edge")?
    5. **Feature Bullets** — Exactly 5? Each under 12 words? Specific, not vague?
    6. **Factual Accuracy** — Do claims match what the raw specs would support?
       No invented specs or exaggerated performance numbers?
    7. **SEO Keywords** — 5 realistic search terms included? Terms a real
       shopper would type into Amazon or Google?
    8. **Readability** — Short sentences? No jargon without context?
       Could a non-technical shopper understand it?
    9. **Persuasion** — Does it make someone want to buy? Clear value proposition?
    10. **Completeness** — All 5 sections present?

    **CRITICAL DECISION RULE — READ CAREFULLY:**
    - Calculate the total score out of 100.
    - If total >= 78: You MUST call the `exit_loop` tool IMMEDIATELY to approve
      and stop the refinement loop. Do not just say "APPROVED" — you must call
      the tool. Failing to call the tool will cause the loop to continue
      unnecessarily and waste resources.
    - If total < 78: Do NOT call exit_loop. Instead, provide specific,
      actionable feedback for every criterion scoring below 8.

    **Output format:**
    Score: X/100
    Status: APPROVED (and exit_loop called) or NEEDS REVISION
    Breakdown: (score per criterion)
    Feedback: (specific fixes needed, or "All criteria met — listing approved.")
    """,
    description="Audits the product listing and calls exit_loop when it passes.",
    tools=[exit_loop],
    output_key="qa_feedback",
)


# --- Assemble the Loop ---
product_description_loop = LoopAgent(
    name="ProductDescriptionLoop",
    sub_agents=[product_writer_agent, qa_auditor_agent],
    max_iterations=4,
    description="Iteratively writes and refines a product listing until QA approves.",
)

root_agent = product_description_loop