from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.llm_agent import LlmAgent

# --- Constants ---
GEMINI_MODEL = "gemini-3.1-pro-preview"

# --- Stage 1: Email Classifier ---
# Reads the raw customer email and categorizes it.
email_classifier_agent = LlmAgent(
    name="EmailClassifierAgent",
    model=GEMINI_MODEL,
    instruction="""
    You are a Customer Support Email Classifier.

    Analyze the following customer email and classify it into exactly ONE category:
    - BILLING: Payment issues, refund requests, invoice questions, subscription problems
    - TECHNICAL: Bug reports, feature not working, integration issues, error messages
    - ACCOUNT: Login problems, password reset, account deletion, profile changes
    - SHIPPING: Delivery delays, tracking issues, wrong address, lost packages
    - FEEDBACK: Compliments, suggestions, feature requests, general opinions
    - ESCALATION: Threats to leave, legal mentions, repeated unresolved complaints

    Also extract:
    - **Customer Name** (if mentioned, otherwise "Unknown")
    - **Product/Service** mentioned (if any, otherwise "General")
    - **Urgency** (LOW / MEDIUM / HIGH / CRITICAL)

    **Output format (strictly follow this):**
    Category: <category>
    Customer Name: <name>
    Product/Service: <product>
    Urgency: <urgency>
    Summary: <one-line summary of the issue>
    """,
    description="Classifies incoming customer emails by category and urgency.",
    output_key="email_classification",
)

# --- Stage 2: Sentiment Analyzer ---
# Analyzes the emotional tone of the customer email.
sentiment_analyzer_agent = LlmAgent(
    name="SentimentAnalyzerAgent",
    model=GEMINI_MODEL,
    instruction="""
    You are a Customer Sentiment Analyst.

    Based on the original customer email AND the classification below,
    analyze the customer's emotional state.

    **Classification:**
    {email_classification}

    **Analyze and output the following:**
    - **Sentiment:** POSITIVE / NEUTRAL / NEGATIVE / ANGRY / FRUSTRATED
    - **Tone:** Polite / Neutral / Impatient / Hostile / Desperate
    - **Recommended Response Tone:** Empathetic / Professional / Apologetic / Celebratory / Urgent
    - **Key Emotional Triggers:** List 1-3 phrases from the email that indicate the customer's mood.
    - **De-escalation Needed:** YES / NO

    Output *only* the analysis in the format above.
    """,
    description="Analyzes customer sentiment and recommends response tone.",
    output_key="sentiment_analysis",
)

# --- Stage 3: Response Drafter ---
# Drafts a professional reply based on classification and sentiment.
response_drafter_agent = LlmAgent(
    name="ResponseDrafterAgent",
    model=GEMINI_MODEL,
    instruction="""
    You are a Professional Customer Support Agent.

    Draft a reply to the customer based on the following context:

    **Email Classification:**
    {email_classification}

    **Sentiment Analysis:**
    {sentiment_analysis}

    **Guidelines:**
    1. Address the customer by name (if known).
    2. Match the recommended response tone from the sentiment analysis.
    3. Acknowledge their specific issue directly — never be generic.
    4. Provide a clear next step or resolution path.
    5. If de-escalation is needed, lead with empathy and offer concrete remediation
       (e.g., discount, expedited shipping, direct callback).
    6. Keep the email between 80-150 words.
    7. End with a professional sign-off from "The Support Team".

    **Output:**
    Output *only* the complete email reply. Do not include subject line or metadata.
    """,
    description="Drafts a professional customer support response.",
    output_key="draft_response",
)

# --- Stage 4: Quality Checker ---
# Reviews the drafted response for quality before it's sent.
quality_checker_agent = LlmAgent(
    name="QualityCheckerAgent",
    model=GEMINI_MODEL,
    instruction="""
    You are a Customer Support Quality Assurance Specialist.

    Review the drafted response below against the original context.

    **Email Classification:**
    {email_classification}

    **Sentiment Analysis:**
    {sentiment_analysis}

    **Draft Response:**
    {draft_response}

    **Quality Checklist:**
    1. ✅ Does it address the specific issue mentioned in the classification?
    2. ✅ Is the tone appropriate given the sentiment analysis?
    3. ✅ Does it include a clear next step or resolution?
    4. ✅ Is it free of grammar and spelling errors?
    5. ✅ Is it within 80-150 words?
    6. ✅ Does it use the customer's name (if available)?
    7. ✅ If de-escalation was needed, does it offer concrete remediation?

    **Output:**
    - If the draft passes ALL checks, output: "APPROVED" followed by the original draft unchanged.
    - If the draft FAILS any check, output: "REVISED" followed by your corrected version
      of the full email, with a brief note on what you changed at the end.
    """,
    description="Reviews and approves or revises the drafted response.",
    output_key="final_response",
)


# --- Assemble the Sequential Pipeline ---
customer_support_pipeline = SequentialAgent(
    name="CustomerSupportPipeline",
    sub_agents=[
        email_classifier_agent,
        sentiment_analyzer_agent,
        response_drafter_agent,
        quality_checker_agent,
    ],
    description="End-to-end customer support email processing pipeline: classify → analyze sentiment → draft reply → quality check.",
)

root_agent = customer_support_pipeline