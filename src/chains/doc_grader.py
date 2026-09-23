"""
Document Relevance Grader.
Avalia se um chunk de documento recuperado possui relacao semantica e factual
com a questao investigativa do usuario.
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL


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
