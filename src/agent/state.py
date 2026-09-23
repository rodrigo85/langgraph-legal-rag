"""
Contrato de Dados e Estado do Agente (State Schema).
Define o contrato tipado que transita entre todos os nos do DAG no LangGraph.
"""

from typing import List, Optional
from typing_extensions import TypedDict
from langchain_core.documents import Document


class AgentState(TypedDict):
    """
    Contrato de Estado Unificado do LangGraph.
    Garante a rastreabilidade e integridade dos dados durante as transicoes de estado.
    """
    question: str                         # Pergunta original submetida pelo usuario
    current_query: str                    # Query ativa usada para busca vetorial (otimizada)
    documents: List[Document]             # Colecao de chunks da camada Gold aprovados pelo grader
    generation: str                       # Resposta sintetizada pelo LLM
    generation_attempts: int              # Contador de geracoes consecutivas no mesmo conjunto de chunks
    retry_count: int                      # Contador de ciclos de autocorrecao
    max_retries: int                      # Limite maximo de retroalimentacoes no DAG
    web_search_needed: bool               # Flag indicando necessidade de busca externa complementar
    hallucination_verdict: Optional[str]  # "grounded" (fiel) ou "hallucinated" (alucinou)
    answer_verdict: Optional[str]         # "useful" (respondeu) ou "not_useful" (insuficiente)
    citations: List[str]                  # Linhagem de paginas comprovadas da sentenca
    as_of_date: Optional[str]             # Data limite Point-in-Time YYYY-MM-DD (Anti-Lookahead Bias)
    milestone_title: Optional[str]        # Titulo do marco processual em vigor


