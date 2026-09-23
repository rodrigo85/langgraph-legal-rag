"""
Hallucination Grader Chain.
Audita se cada afirmacao factual contida na resposta gerada pelo LLM
possui respaldo direto nos documentos recuperados (Grounding Check).
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL, OLLAMA_KEEP_ALIVE


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
        keep_alive=OLLAMA_KEEP_ALIVE,
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


class UnifiedQualityAudit(BaseModel):
    """Auditoria consolidada de fidelidade factual (grounding) e utilidade da resposta."""
    is_grounded: Literal["yes", "no"] = Field(
        description="A resposta esta 100% ancorada nos documentos fornecidos, sem inventar fatos ou numeros? 'yes' ou 'no'"
    )
    is_useful: Literal["yes", "no"] = Field(
        description="A resposta atende e resolve a duvida investigativa do usuario de forma pertinente? 'yes' ou 'no'"
    )
    audit_summary: str = Field(
        description="Resumo do veredito (1 linha) em portugues."
    )


def create_unified_quality_grader():
    """
    Cria auditor unificado que valida Grounding e Utilidade em uma unica inferencia.
    Economiza 50% do tempo de auditoria final.
    """
    llm = ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=0,
        base_url=OLLAMA_BASE_URL,
        num_predict=150,
        keep_alive=OLLAMA_KEEP_ALIVE,
    )

    system_prompt = """Voce e o Auditor Chefe de Qualidade e Integridade Factual do sistema de IA pericial.
Sua missao e auditar a resposta gerada sob dois criterios rigorosos:

1. Fidelidade Factual (is_grounded):
- 'yes': Se TODAS as afirmacoes, acordos, numeros e citacoes sao estritamente suportadas pelo contexto documental.
- 'no': Se a resposta trouxer dados ou fatos que NAO constam nos documentos fornecidos (alucinacao).

2. Utilidade da Resposta (is_useful):
- 'yes': Se a resposta aborda diretamente a pergunta feita pelo usuario.
- 'no': Se a resposta for evasiva, vaga ou fugir do questionamento.

Escreva o resumo ('audit_summary') em portugues."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Contexto Documental:\n{documents}\n\nPergunta do Usuario:\n{question}\n\nResposta Gerada:\n{generation}\n\nAvalie a fidelidade e a utilidade da resposta:"),
    ])

    structured_llm = llm.with_structured_output(UnifiedQualityAudit)
    return prompt | structured_llm
