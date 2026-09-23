"""
Hallucination Grader Chain.
Audita se cada afirmacao factual contida na resposta gerada pelo LLM
possui respaldo direto nos documentos recuperados (Grounding Check).
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL


class GradeHallucinations(BaseModel):
    """Modelo de dados para a auditoria de alucinacao / ancoragem."""
    binary_score: Literal["yes", "no"] = Field(
        description="A resposta esta estritamente ancorada nos fatos fornecidos? 'yes' (sem alucinacao) ou 'no' (ha alucinacao ou invencao de dados)"
    )
    explanation: str = Field(
        description="Breve explicacao detalhando se algum dado (numero, ano, citacao) foi inventado ou se tudo bate com o contexto."
    )


def create_hallucination_grader():
    """
    Cria a chain de deteccao de alucinacoes factuais.
    """
    llm = ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=0,
        base_url=OLLAMA_BASE_URL,
        num_predict=150,
    )

    system_prompt = """Voce e um Auditor de Integridade Factual de Inteligencia Artificial.
Sua unica tarefa e avaliar se a resposta gerada esta 100% ancorada (grounded) nos fatos contidos nos trechos de documentos fornecidos.

Criterios:
- Se TODAS as afirmacoes, numeros, datas e citacoes presentes na resposta sao suportadas pelos trechos: atribua 'yes'.
- Se a resposta trouxer informacoes externas que NAO constam nos trechos fornecidos, inventar numeros ou desvirtuar fatos: atribua 'no'.
- Escreva a explicacao ('explanation') 100% em PORTUGUES.

Seja rigoroso: fatos nao mencionados nos trechos devem ser considerados alucinacao."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Trechos dos Documentos Fornecidos:\n{documents}\n\nResposta Gerada:\n{generation}\n\nAvalie se a resposta e fiel aos documentos:"),
    ])

    structured_llm = llm.with_structured_output(GradeHallucinations)
    return prompt | structured_llm
