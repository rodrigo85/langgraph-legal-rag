"""
Answer Grader Chain.
Audita se a resposta gerada de fato resolve e responde a pergunta original do usuario.
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL


class GradeAnswer(BaseModel):
    """Modelo de dados para a avaliacao de utilidade da resposta."""
    binary_score: Literal["yes", "no"] = Field(
        description="A resposta resolve a pergunta do usuario? 'yes' ou 'no'"
    )
    explanation: str = Field(
        description="Breve explicacao do motivo pelo qual a resposta atendeu ou nao ao questionamento."
    )


def create_answer_grader():
    """
    Cria a chain de verificacao de pertinencia e utilidade da resposta.
    """
    llm = ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=0,
        base_url=OLLAMA_BASE_URL,
        num_predict=150,
    )

    system_prompt = """Voce e um Revisor de Qualidade de Respostas de IA.
Sua missao e julgar se a resposta fornecida de fato responde ao questionamento feito pelo usuario.

Criterios:
- Se a resposta aborda e responde diretamente o que foi perguntado: 'yes'.
- Se a resposta for evasiva, fugir do assunto ou deixar a pergunta central sem solucao: 'no'.

Responda no formato estruturado."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Pergunta do Usuario:\n{question}\n\nResposta Fornecida:\n{generation}\n\nAvalie se a pergunta foi respondida com sucesso:"),
    ])

    structured_llm = llm.with_structured_output(GradeAnswer)
    return prompt | structured_llm
