"""
Query Rewriter.
Rewrites vague or informally worded investigative questions into the formal legal
and contractual terminology of the U.S. v. Google antitrust case.
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from legal_rag.providers import get_chat_model


class RewrittenQuery(BaseModel):
    """Modelo de dados para a query otimizada."""

    improved_query: str = Field(
        description="A pergunta reescrita em termos tecnicos judiciais, nomes proprios e termos contratuais em ingles."
    )
    rationale: str = Field(description="O motivo da reescrita e quais entidades juridicas/termos foram inseridos.")


def create_query_rewriter():
    """
    Builds the query transformation chain to maximize semantic recall.
    """
    llm = get_chat_model(temperature=0.2, max_tokens=150)

    system_prompt = """Voce e um assistente juridico especializado no processo federal antitruste U.S. v. Google (Doc 1033 - Sentenca do Juiz Amit Mehta).
O documento original esta em ingles e contem jargoes tecnicos especificos como:
- ISA (Information Services Agreement - contrato de busca padrao entre Google e Apple)
- RSA (Revenue Share Agreement com Samsung e operadoras)
- Depoimentos de Satya Nadella (Microsoft), Sundar Pichai (Google), Eddy Cue (Apple)
- Queries, default placement, scale, distribution channels, general search text ads, queries per day.

Sua tarefa e pegar a pergunta do usuario (que pode estar em portugues e ser informal) e reescreve-la em termos precisos de busca (em ingles com palavras-chave contratuais) para que o banco vetorial localize as paginas e clausulas exatas da sentenca."""

    re_write_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "Pergunta original: {question}\n\nReescreva esta query com termos contratuais e nomes proprios adequados:",
            ),
        ]
    )

    structured_llm = llm.with_structured_output(RewrittenQuery)
    return re_write_prompt | structured_llm
