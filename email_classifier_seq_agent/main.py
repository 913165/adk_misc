import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from email_classifier_seq_agent.agent import root_agent


# --- Sample Customer Emails (swap these out to test different scenarios) ---
SAMPLE_EMAILS = {
    "angry_billing": """
        Subject: THIS IS RIDICULOUS - CHARGED TWICE!!

        Hi,
        My name is Rajesh Sharma. I was charged TWICE for my Pro subscription
        this month — ₹1,998 instead of ₹999. I've been a loyal customer for
        2 years and this is unacceptable. I've already contacted my bank.

        If this isn't resolved within 24 hours, I'm cancelling everything and
        switching to your competitor. Fix this NOW.

        Order ID: #ORD-88412
    """,
    "polite_technical": """
        Hi Support Team,

        I'm Sarah and I've been using your Analytics Dashboard for a few weeks.
        Love the product overall! However, I noticed that the CSV export feature
        seems to be broken since the last update — it downloads an empty file
        every time I try.

        I'm on the Business plan, using Chrome on macOS. Could you look into this?

        Thanks so much!
        Sarah
    """,
    "shipping_issue": """
        Hello,

        I ordered a Wireless Keyboard (Order #WK-20256) on April 2nd with
        express shipping. It's now April 15th and I still haven't received it.
        The tracking page has said "In Transit" for 9 days without any update.

        I need this for work. Can someone please look into this urgently?

        - Priya Nair
    """,
}


async def run_pipeline(email_key: str):
    """Run the support pipeline for a given sample email."""
    session_service = InMemorySessionService()

    runner = Runner(
        agent=root_agent,
        app_name="customer_support_app",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="customer_support_app",
        user_id="support_agent_1",
    )

    customer_email = SAMPLE_EMAILS[email_key]

    content = types.Content(
        role="user",
        parts=[types.Part(text=customer_email)],
    )

    print(f"{'=' * 70}")
    print(f"  PROCESSING: {email_key}")
    print(f"{'=' * 70}")
    print(f"\n📩 Incoming Email:\n{customer_email.strip()}\n")
    print("-" * 70)

    async for event in runner.run_async(
        user_id="support_agent_1",
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            author = event.author or "Agent"
            text = "\n".join(p.text for p in event.content.parts if p.text)
            if text.strip():
                # Pretty-print each stage
                stage_icons = {
                    "EmailClassifierAgent": "🏷️  CLASSIFICATION",
                    "SentimentAnalyzerAgent": "💡 SENTIMENT ANALYSIS",
                    "ResponseDrafterAgent": "✍️  DRAFT RESPONSE",
                    "QualityCheckerAgent": "✅ QUALITY CHECK",
                }
                label = stage_icons.get(author, author)
                print(f"\n{'─' * 40}")
                print(f"  {label}")
                print(f"{'─' * 40}")
                print(text.strip())

    print(f"\n{'=' * 70}")
    print("  PIPELINE COMPLETE")
    print(f"{'=' * 70}\n\n")


async def main():
    # Process all sample emails
    for email_key in SAMPLE_EMAILS:
        await run_pipeline(email_key)


if __name__ == "__main__":
    asyncio.run(main())