"""
Google ADK agent with custom RAG tools backed by Redis vector search.
"""

import os
from google.adk.agents import Agent
from dotenv import load_dotenv

from . import tools

load_dotenv()

SYSTEM_INSTRUCTION = """You are a helpful PDF document assistant. You answer questions
about documents that have been uploaded and indexed.

**How to answer questions:**
1. ALWAYS use the `search_documents` tool first to retrieve relevant passages from
   the indexed PDFs before answering a question.
2. Base your answer strictly on the retrieved context. If the context does not contain
   enough information, say so honestly.
3. Cite the source filename and page number when referencing specific information,
   e.g. "(source: report.pdf, page 3)".
4. If the user asks which documents are available, use the `list_documents` tool.
5. If no documents are indexed yet, tell the user to upload PDFs first.

**Style guidelines:**
- Be concise and direct.
- Use bullet points for multi-part answers.
- If the user's question is ambiguous, ask for clarification.
"""

root_agent = Agent(
    model=os.getenv("ADK_MODEL", "gemini-2.0-flash"),
    name="pdf_rag_agent",
    description="An agent that answers questions about uploaded PDF documents using RAG with Redis vector search.",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        tools.search_documents,
        tools.list_documents,
    ],
)
