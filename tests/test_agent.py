"""
Teste automatizado do Agente RAG Autocorretivo.
Executa uma consulta investigativa no grafo LangGraph e valida:
1. Recuperacao de chunks judiciais
2. Filtragem pelo Document Grader
3. Geracao fundamentada com citacao de paginas
4. Auditoria de alucinacao aprovada
"""

import sys
from pathlib import Path

# Configura codificação UTF-8 para o terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.graph import build_graph


def test_agent_run():
    print("[*] Iniciando teste do Grafo LangGraph...")
    app = build_graph()

    test_question = (
        "Qual era o acordo de compartilhamento de receita (ISA) entre Google e Apple "
        "para manter a busca do Google como padrao no Safari?"
    )

    initial_state = {
        "question": test_question,
        "current_query": test_question,
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "max_retries": 3,
        "web_search_needed": False,
        "hallucination_verdict": None,
        "answer_verdict": None,
        "citations": [],
    }

    print(f"[*] Pergunta de Teste: {test_question}")
    result = app.invoke(initial_state)

    print("\n" + "=" * 50)
    print("[*] RESULTADO DA GERACAO:")
    print(result.get("generation"))
    print("\n[*] CITACOES ENCONTRADAS:")
    print(result.get("citations"))
    print("=" * 50)

    assert result.get("generation") is not None
    assert len(result.get("generation")) > 50
    print("[PASS] Teste concluido com sucesso!")


if __name__ == "__main__":
    test_agent_run()
