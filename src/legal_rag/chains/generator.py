"""
Generator Chain.
Generates the final investigative answer strictly grounded in the retrieved documents,
with mandatory page citations from Judge Amit Mehta's opinion.
"""

import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from legal_rag.providers import get_chat_model


def sanitize_response(text: str) -> str:
    """Sanitizes the generated text, stripping any residual CJK characters."""
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
    Builds the grounded answer synthesis chain.
    """
    llm = get_chat_model(temperature=0.1, max_tokens=600)

    system_prompt = """Voce e um Perito Forense e Pesquisador Especialista no processo antitruste federal U.S. v. Google LLC.
Sua missao e fornecer respostas objetivas, diretas e 100% ancoradas nas evidencias documentais fornecidas nos trechos abaixo.

Regras Inegociaveis:
1. Idioma exclusivo: Redija a resposta 100% em PORTUGUES formal (Brasil). Todas as explicacoes e analises devem estar estritamente na norma culta da lingua portuguesa.
2. Limite sua resposta a 2 ou 3 paragrafos concisos e diretos ao ponto.
3. CITE OBRIGATORIAMENTE o numero da pagina de onde cada fato foi extraido, usando o formato: [Pag. X da Sentenca].
4. NUNCA invente ou presuma acordos, porcentagens, valores ou datas que nao estejam expressamente no contexto.
5. Se o contexto contiver mencao a depoimentos sob juramento (ex: Satya Nadella, Sundar Pichai, Eddy Cue) ou e-mails internos (UPX exhibits), destaque essas fontes literais.
6. TABELAS DE DEPOENTES: Diferencie rigorosamente a 'Affiliation' (empresa do depoente) de quem o convocou ('Called By'). So declare que alguem e da Google se a Affiliation for expressamente Google. Se os trechos nao responderem com certeza quem foi a testemunha principal chamada a depor, declare claramente que as evidencias nos trechos sao inconclusivas em vez de supor."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "Contexto Documental Recuperado:\n{context}\n\nPergunta Investigativa:\n{question}\n\nResposta fundamentada com citacoes:",
            ),
        ]
    )

    return prompt | llm | StrOutputParser() | RunnableLambda(sanitize_response)
