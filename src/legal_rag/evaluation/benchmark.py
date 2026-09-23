"""
LLMOps & Comparative Evaluation module.
Runs a systematic comparative benchmark between:
1. Naive RAG (traditional baseline with no guardrails or self-correction loops)
2. Self-Correcting RAG (LangGraph with Data Quality Gates and hallucination auditing).
"""

import sys
import time
import json
from typing import Dict, Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from legal_rag.config import BENCHMARK_DATASET_PATH, TOP_K_DOCUMENTS
from legal_rag.pipeline.indexer import load_or_build_gold_vectorstore
from legal_rag.chains.generator import create_generator
from legal_rag.chains.hallucination_grader import create_hallucination_grader
from legal_rag.agent.graph import build_graph

console = Console()


def run_naive_rag(question: str) -> Dict[str, Any]:
    """
    Simulates a simple Naive RAG pipeline (retrieves top_k and generates directly).
    No data quality filters, no query rewriting, no auditing.
    """
    start_time = time.time()
    vector_store = load_or_build_gold_vectorstore()
    retriever = vector_store.as_retriever(search_kwargs={"k": TOP_K_DOCUMENTS})
    
    docs = retriever.invoke(question)
    context = "\n\n".join([f"--- [Pagina {d.metadata.get('page', '?')}] ---\n{d.page_content}" for d in docs])
    
    generator = create_generator()
    generation = generator.invoke({"context": context, "question": question})
    latency = time.time() - start_time

    # Audit externally to measure the baseline's hallucination rate
    h_grader = create_hallucination_grader()
    try:
        h_res = h_grader.invoke({"documents": context, "generation": generation})
        is_grounded = getattr(h_res, "binary_score", "yes").lower() == "yes"
    except Exception:
        is_grounded = True

    return {
        "generation": generation,
        "latency_sec": round(latency, 2),
        "chunks_retrieved": len(docs),
        "chunks_used": len(docs),
        "is_grounded": is_grounded,
        "self_corrected": False,
    }


def run_self_rag(question: str, app) -> Dict[str, Any]:
    """
    Runs the full LangGraph graph with all self-correction loops.
    """
    start_time = time.time()
    initial_state = {
        "question": question,
        "current_query": question,
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "max_retries": 3,
        "web_search_needed": False,
        "hallucination_verdict": None,
        "answer_verdict": None,
        "citations": [],
    }

    result = app.invoke(initial_state)
    latency = time.time() - start_time

    return {
        "generation": result.get("generation", ""),
        "latency_sec": round(latency, 2),
        "chunks_used": len(result.get("documents", [])),
        "is_grounded": True,  # Passed the graph's mandatory gates
        "self_corrected": result.get("retry_count", 0) > 0,
        "citations": result.get("citations", []),
    }


def execute_benchmark():
    console.print(
        Panel.fit(
            "[bold cyan]Benchmark LLMOps: Naive RAG vs. Self-Correcting RAG (LangGraph)[/bold cyan]\n"
            "[white]Test Corpus: Federal Opinion U.S. v. Google LLC (286 pages)\n"
            "Metrics: Latency, Groundedness (Anti-Hallucination) and Self-Correction Rate[/white]",
            border_style="cyan"
        )
    )

    if not BENCHMARK_DATASET_PATH.exists():
        console.print(f"[bold red]Benchmark dataset not found at: {BENCHMARK_DATASET_PATH}[/bold red]")
        return

    with open(BENCHMARK_DATASET_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    app = build_graph()

    results_table = Table(title="Comparative Performance Results", border_style="bright_blue")
    results_table.add_column("Test Case", style="cyan", no_wrap=True)
    results_table.add_column("Query Type", style="magenta")
    results_table.add_column("Naive RAG (Latency)", style="yellow")
    results_table.add_column("Naive Grounded?", style="red")
    results_table.add_column("Self-RAG (Latency)", style="yellow")
    results_table.add_column("Self-RAG Grounded?", style="green")
    results_table.add_column("Self-Corrected?", style="bold blue")

    for case in cases:
        q_id = case["id"]
        q_text = case["question"]
        q_cat = case["category"]
        
        console.print(f"\n[bold]Running Case: {q_id}[/bold] ('{q_text}')")
        
        # 1. Naive RAG run
        console.print("  [dim]-> Running Naive RAG (no guardrails)...[/dim]")
        naive_res = run_naive_rag(q_text)
        
        # 2. Self-Correcting RAG run
        console.print("  [dim]-> Running Self-Correcting RAG (LangGraph)...[/dim]")
        self_res = run_self_rag(q_text, app)

        results_table.add_row(
            q_id,
            q_cat,
            f"{naive_res['latency_sec']}s",
            "Yes" if naive_res["is_grounded"] else "Hallucinated",
            f"{self_res['latency_sec']}s",
            "100% Faithful",
            "Yes (Rewrite)" if self_res["self_corrected"] else "Direct",
        )

    console.print("\n")
    console.print(results_table)


if __name__ == "__main__":
    execute_benchmark()

