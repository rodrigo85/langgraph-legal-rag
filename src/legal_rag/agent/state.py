"""
Agent State Schema (Data Contract).
Defines the typed contract passed between all nodes of the LangGraph DAG.
"""

from typing import List, Optional
from typing_extensions import TypedDict
from langchain_core.documents import Document


class AgentState(TypedDict):
    """
    Unified LangGraph state contract.
    Ensures data traceability and integrity across state transitions.
    """
    question: str                         # Original question submitted by the user
    current_query: str                    # Active (optimized) query used for vector search
    documents: List[Document]             # Gold-layer chunks approved by the grader
    generation: str                       # Answer synthesized by the LLM
    generation_attempts: int              # Consecutive generations on the same chunk set
    retry_count: int                      # Self-correction cycle counter
    max_retries: int                      # Maximum number of feedback loops in the DAG
    web_search_needed: bool               # Whether a complementary external search is needed
    hallucination_verdict: Optional[str]  # "grounded" (faithful) or "hallucinated"
    answer_verdict: Optional[str]         # "useful" (answered) or "not_useful" (insufficient)
    citations: List[str]                  # Lineage of supporting opinion pages
    as_of_date: Optional[str]             # Point-in-Time cutoff date YYYY-MM-DD (anti-lookahead bias)
    milestone_title: Optional[str]        # Title of the procedural milestone in effect


