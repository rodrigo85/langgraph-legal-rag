"""
Document Relevance Grader.
Avalia se um chunk de documento recuperado possui relacao semantica e factual
com a questao investigativa do usuario.
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL, OLLAMA_KEEP_ALIVE


class GradeDocuments(BaseModel):
    """Modelo de dados para a avaliacao de relevancia do documento."""
    binary_score: Literal["yes", "no"] = Field(
        description="O documento e relevante para a questao? 'yes' ou 'no'"
    )
    reason: str = Field(
        description="Breve explicacao (1 linha) do motivo pelo qual e ou nao e relevante."
    )


def create_doc_grader():
    """
    Cria a chain de avaliacao de relevancia com saida estruturada.
    """
    llm = ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=0,
        base_url=OLLAMA_BASE_URL,
        num_predict=150,
        keep_alive=OLLAMA_KEEP_ALIVE,
    )

    system_prompt = """Voce e um perito judicial avaliando a relevancia de trechos de documentos judiciais do caso U.S. v. Google.
Sua funcao e classificar se o trecho recuperado contem informacoes, palavras-chave, dados ou termos contratuais pertinentes para responder a pergunta.

Avalie com o seguinte criterio:
- Se o documento contiver termos diretamente relacionados ou pistas relevantes para a pergunta: 'yes'.
- Se o documento falar de outro assunto desconexo ou meras questoes processuais sem ligacao: 'no'.
- Escreva a justificativa ('reason') 100% em PORTUGUES.

Responda estritamente no formato estruturado solicitado."""

    grader_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Trecho do Documento:\n\n{document}\n\nPergunta do Usuario: {question}"),
    ])

    structured_llm = llm.with_structured_output(GradeDocuments)
    return grader_prompt | structured_llm


class BatchGradeDocuments(BaseModel):
    """Modelo de dados para a avaliacao em lote (batch) de múltiplos chunks."""
    relevant_indices: list[int] = Field(
        description="Lista contendo os numeros (indices) dos trechos relevantes (ex: [1, 3] ou [2, 4]). Se nenhum for relevante, envie []."
    )
    rationale: str = Field(
        description="Breve explicacao (1 linha) da selecao dos trechos relevantes."
    )


def create_batch_doc_grader():
    """
    Cria a chain de avaliacao em lote que processa TODOS os chunks em uma unica inferencia.
    Reduz a latencia da filtragem em ate 75%.
    """
    llm = ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=0,
        base_url=OLLAMA_BASE_URL,
        num_predict=150,
        keep_alive=OLLAMA_KEEP_ALIVE,
    )

    system_prompt = """Voce e um perito judicial avaliando a relevancia de trechos de documentos judiciais do caso U.S. v. Google.
Sua funcao e analisar a lista de trechos numerados e identificar quais deles contem informacoes, nomes, clausulas ou termos pertinentes para responder a pergunta investigativa.

Instrucoes:
- Retorne em 'relevant_indices' a lista de numeros dos trechos pertinentes (ex: [1, 2, 4]).
- Se todos forem relevantes, inclua todos os indices.
- Se nenhum contiver informacoes pertinentes, retorne lista vazia [].
- Escreva a justificativa ('rationale') concisamente em portugues."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Pergunta Investigativa:\n{question}\n\nTrechos Recuperados:\n{documents_batch}"),
    ])

    structured_llm = llm.with_structured_output(BatchGradeDocuments)
    return prompt | structured_llm
