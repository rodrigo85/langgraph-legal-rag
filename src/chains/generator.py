"""
Generator Chain.
Gera a resposta investigativa final estritamente ancorada nos fatos dos documentos recuperados,
com citacao mandatoria das paginas da sentenca do Juiz Amit Mehta.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from src.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL, OLLAMA_KEEP_ALIVE


import re
from langchain_core.runnables import RunnableLambda


def sanitize_response(text: str) -> str:
    """Higieniza o texto gerado, expurgando quaisquer caracteres CJK residuais."""
    lines = text.split("\n")
    valid_lines = []
    for line in lines:
        if re.search(r"[\u4e00-\u9fff]", line):
            line_cleaned = re.sub(r"[\u4e00-\u9fff\u3000-\u303f\uff01-\uffee]+", "", line).strip()
            if len(line_cleaned) > 10:
                valid_lines.append(line_cleaned)
        else:
            valid_lines.append(line)
    return "\n".join(valid_lines).strip()


def create_generator():
    """
    Cria a chain de sintese de resposta fundamentada.
    """
    llm = ChatOllama(
        model=OLLAMA_LLM_MODEL,
        temperature=0.1,
        base_url=OLLAMA_BASE_URL,
        num_predict=600,
        keep_alive=OLLAMA_KEEP_ALIVE,
    )

    system_prompt = """Voce e um Perito Forense e Pesquisador Especialista no processo antitruste federal U.S. v. Google LLC.
Sua missao e fornecer respostas objetivas, diretas e 100% ancoradas nas evidencias documentais fornecidas nos trechos abaixo.

Regras Inegociaveis:
1. Idioma exclusivo: Redija a resposta 100% em PORTUGUES formal (Brasil). Todas as explicacoes e analises devem estar estritamente na norma culta da lingua portuguesa.
2. Limite sua resposta a 2 ou 3 paragrafos concisos e diretos ao ponto.
3. CITE OBRIGATORIAMENTE o numero da pagina de onde cada fato foi extraido, usando o formato: [Pag. X da Sentenca].
4. NUNCA invente ou presuma acordos, porcentagens, valores ou datas que nao estejam expressamente no contexto.
5. Se o contexto contiver mencao a depoimentos sob juramento (ex: Satya Nadella, Sundar Pichai, Eddy Cue) ou e-mails internos (UPX exhibits), destaque essas fontes literais.
6. TABELAS DE DEPOENTES: Diferencie rigorosamente a 'Affiliation' (empresa do depoente) de quem o convocou ('Called By'). So declare que alguem e da Google se a Affiliation for expressamente Google. Se os trechos nao responderem com certeza quem foi a testemunha principal chamada a depor, declare claramente que as evidencias nos trechos sao inconclusivas em vez de supor."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Contexto Documental Recuperado:\n{context}\n\nPergunta Investigativa:\n{question}\n\nResposta fundamentada com citacoes:"),
    ])

    return prompt | llm | StrOutputParser() | RunnableLambda(sanitize_response)
