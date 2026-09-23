"""
Interactive CLI for the self-correcting RAG agent (DOJ v. Google).
"""

import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from legal_rag.agent.graph import build_graph
from legal_rag.config import get_settings
from legal_rag.observability import configure_logging

console = Console()


def run_cli():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows terminals default to a legacy code page
    configure_logging()
    settings = get_settings()

    console.print(
        Panel.fit(
            "[bold cyan]Self-Correcting RAG Agent (Self-RAG) - U.S. v. Google[/bold cyan]\n"
            "[white]Court record: DOJ Complaint (Doc 1), Liability Opinion (Doc 1033), "
            "DOJ Proposed Final Judgment on Remedies (Doc 1062-1)\n"
            f"Architecture: LangGraph + vector store '{settings.vector_store}' + LLM provider "
            f"'{settings.llm_provider}' (set VECTOR_STORE / LLM_PROVIDER)[/white]",
            border_style="cyan",
        )
    )

    console.print("[dim]Compiling the state graph...[/dim]")
    app = build_graph()
    console.print("[bold green][OK] Graph loaded and ready for queries![/bold green]\n")

    examples = [
        "Qual era a porcentagem da receita que o Google repassava para a Apple no contrato ISA em 2016 e anos seguintes?",
        "O que Satya Nadella (Microsoft) testemunhou sob juramento sobre o Bing conseguir competir caso a Apple nao o adotasse?",
        "Qual foi o valor total pago pelo Google em acordos de receita (revenue share) para ser o buscador padrao em 2021?",
    ]

    console.print("[bold yellow]Exemplos de perguntas investigativas para testar:[/bold yellow]")
    for i, ex in enumerate(examples, 1):
        console.print(f"  [cyan]{i}.[/cyan] {ex}")
    console.print()

    while True:
        try:
            question = Prompt.ask("[bold green]Pergunta Investigativa (ou 'sair')[/bold green]")
            if not question or question.strip().lower() in ["sair", "exit", "quit", "q"]:
                console.print("[bold yellow]Encerrando sessao.[/bold yellow]")
                break

            initial_state = {
                "question": question,
                "current_query": question,
                "documents": [],
                "generation": "",
                "generation_attempts": 0,
                "retry_count": 0,
                "max_retries": settings.max_retries,
                "web_search_needed": False,
                "hallucination_verdict": None,
                "answer_verdict": None,
                "citations": [],
            }

            console.print("\n[bold cyan]=== STARTING GRAPH EXECUTION ===[/bold cyan]")

            final_state = dict(initial_state)
            for output in app.stream(initial_state):
                for node_name, state_update in output.items():
                    console.print(f"[bold magenta]>>> Node completed: {node_name}[/bold magenta]")
                    final_state.update(state_update)

            console.print("\n" + "=" * 60)
            console.print(
                Panel(
                    Markdown(final_state.get("generation", "Sem resposta")),
                    title="[bold green]Resposta Auditada e Fundamentada[/bold green]",
                    border_style="green",
                )
            )

            citations = final_state.get("citations", [])
            if citations:
                console.print(f"[bold yellow]Paginas citadas da Sentenca:[/bold yellow] {', '.join(citations)}")
            console.print("=" * 60 + "\n")

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Interrompido pelo usuario.[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error during execution: {e}[/bold red]")


if __name__ == "__main__":
    run_cli()
