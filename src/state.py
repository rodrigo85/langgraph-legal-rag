from typing import List, Optional
from typing_extensions import TypedDict
from langchain_core.documents import Document


class AgentState(TypedDict):
    """
    Estado compartilhado que flui atraves de todos os nos do grafo LangGraph.
    """
    question: str                         # Pergunta original do usuario
    current_query: str                    # Query ativa usada para recuperacao (pode ser reescrita)
    documents: List[Document]             # Documentos recuperados e aprovados pelo grader
    generation: str                       # Resposta gerada pelo LLM
    retry_count: int                      # Quantidade de tentativas de reescrita/recuperacao
    max_retries: int                      # Limite maximo de reescritas para evitar loops
    web_search_needed: bool               # Flag indicando se busca complementar e necessaria
    hallucination_verdict: Optional[str]  # "grounded" (fiel) ou "hallucinated" (alucinou)
    answer_verdict: Optional[str]         # "useful" (respondeu) ou "not_useful" (nao respondeu)
    citations: List[str]                  # Citacoes de paginas encontradas nos chunks
