"""
Data Augmentation & Chain-of-Thought (CoT) Synthesis Pipeline.
Scans the Silver-layer pages to synthesize:
1. Samples with explicit forensic reasoning (<pensamento_forense>)
2. DPO preference dataset (Chosen vs. Rejected).
These datasets are prepared for a future LoRA fine-tune; no model weights have been trained on them.
"""

import json
import random
from typing import Any, Dict, List

from legal_rag.config import SILVER_CORPUS_JSONL, TRAINING_DATA_DIR

TRAINING_DIR = TRAINING_DATA_DIR
COT_TRAIN_FILE = TRAINING_DIR / "train_cot.jsonl"
DPO_PREF_FILE = TRAINING_DIR / "preference_dataset.jsonl"


def load_silver_pages() -> List[Dict[str, Any]]:
    """Loads the structured Silver-layer pages."""
    if not SILVER_CORPUS_JSONL.exists():
        raise FileNotFoundError(f"Silver file not found at: {SILVER_CORPUS_JSONL}")

    records = []
    with open(SILVER_CORPUS_JSONL, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def build_cot_dataset():
    """
    Synthesizes 150+ samples with forensic Chain-of-Thought (CoT) and structured citations.
    """
    print("[*] Starting Chain-of-Thought (CoT) data synthesis...")
    pages = load_silver_pages()

    cot_samples = []
    dpo_samples = []

    # Golden examples with refined CoT
    golden_cot_scenarios = [
        {
            "query": "Qual era a porcentagem da receita que o Google repassava para a Apple no contrato ISA em 2016 e qual a sua motivacao concorrencial?",
            "thought": "1. Identificar entidades centrais: Google e Apple.\n2. Localizar termo aditivo: Emenda de 2016 do Information Services Agreement (ISA).\n3. Extrair dados quantitativos: 36% da receita liquida de publicidade do Safari.\n4. Mapear motivacao concorrencial: Criar desincentivo financeiro multibilionario para a Apple nao desenvolver buscador proprio.\n5. Enquadramento juridico: Manutencao de monopolio sob Secao 2 do Sherman Act.\n6. Ancorar citacao estrita: [Pag. 114 da Sentenca].",
            "chosen": "### ⚖️ EVIDÊNCIA FACTUAL [Pág. 114 da Sentença]\nConforme registrado expressamente na sentença judicial [Pág. 114], no termo aditivo firmado em 2016 do Information Services Agreement (ISA), o Google concordou em repassar à Apple 36% da receita líquida (net revenue) gerada por pesquisas no Safari.\n\n### 📑 ANÁLISE JURÍDICO-CONCORRENCIAL\nA motivação concorrencial comprovada nos autos era estabelecer um 'desincentivo poderoso' para que a Apple não investisse na criação ou aquisição de seu próprio mecanismo de busca geral. O fluxo bilionário do ISA garantia que a Apple continuasse economicamente dependente do ecossistema de receitas do Google.\n\n### 📌 CONCLUSÃO\nEssa conduta foi enquadrada pelo tribunal como mecanismo anticoncorrencial de exclusão de rivais e preservação do monopólio de busca sob a Seção 2 do Sherman Act [Pág. 114 da Sentença].",
            "rejected": "O Google e a Apple tinham um acordo chamado ISA onde o Google pagava 36% do dinheiro que ganhava com publicidade no Safari. Isso servia para eles ficarem amigos e a Apple não criar um buscador concorrente.",
        },
        {
            "query": "O que Satya Nadella (Microsoft) testemunhou sobre a teoria do Google de que a concorrencia esta a 'apenas um clique de distancia'?",
            "thought": "1. Localizar testemunho: Depoimento juramentado do CEO da Microsoft Satya Nadella.\n2. Analisar tese do Google: Argumento de que mudar o buscador padrao e trivial ('one click away').\n3. Contra-argumento de Nadella: E uma completa ficcao na pratica; o status de default cria inercia insuperavel.\n4. Efeito de escala: Sem a distribuicao padrao na Apple, o Bing nao atinge a escala de queries para aprimorar algoritmos.\n5. Ancorar citacao estrita: [Pag. 245 da Sentenca].",
            "chosen": "### ⚖️ EVIDÊNCIA FACTUAL [Pág. 245 da Sentença]\nEm depoimento sob juramento citado na sentença [Pág. 245], o CEO da Microsoft Satya Nadella desqualificou frontalmente a tese defensiva do Google de que a concorrência estaria a 'apenas um clique de distância', classificando-a categoricamente como uma 'completa ficção' (complete fiction) na prática mercadológica.\n\n### 📑 ANÁLISE JURÍDICO-CONCORRENCIAL\nNadella explicou que o status de mecanismo padrão ('default') confere uma inércia de comportamento quase intransponível no usuário médio. Sem a distribuição padrão nos dispositivos da Apple, o Bing jamais conseguirá atingir o volume e a escala de queries necessários para que seus modelos de indexação e relevância compitam em igualdade de condições.\n\n### 📌 CONCLUSÃO\nO tribunal acolheu o depoimento de Nadella para demonstrar que o poder de monopólio do Google decorre do controle artificial dos pontos de estrangulamento da distribuição [Pág. 245 da Sentença].",
            "rejected": "Satya Nadella disse que essa história de um clique de distância não é verdade. Ele falou que sem o Safari o Bing não consegue ter clientes suficientes para crescer.",
        },
        {
            "query": "O que sao os acordos MADA e RSA que o Google impunha aos fabricantes de smartphones Android?",
            "thought": "1. Identificar sigla MADA: Mobile Application Distribution Agreement.\n2. Identificar sigla RSA: Revenue Sharing Agreement.\n3. Clausula MADA: Condicionamento de acesso a Google Play Store a pre-instalacao em bloco do Google Suite (venda casada/tying).\n4. Clausula RSA: Pagamento de comissao de publicidade apenas se nenhum buscador concorrente for pre-instalado.\n5. Ancorar citacao estrita: [Pag. 113 da Sentenca].",
            "chosen": "### ⚖️ EVIDÊNCIA FACTUAL [Pág. 113 da Sentença]\nDe acordo com a sentença de mérito [Pág. 113], o ecossistema Android foi blindado por dois tipos contratuais interligados:\n1. **MADA (Mobile Application Distribution Agreement)**: Contrato que condicionava a licença da Google Play Store à pré-instalação mandatória de todo o pacote de aplicativos proprietários do Google em posições nobres na tela inicial.\n2. **RSA (Revenue Share Agreement)**: Acordo que compartilhava faturamento publicitário com operadoras e OEMs (como a Samsung), condicionado à exclusividade estrita (nenhum buscador rival pré-instalado).\n\n### 📑 ANÁLISE JURÍDICO-CONCORRENCIAL\nA combinação de MADA e RSA atuou como uma barreira de entrada estrutural intransponível para motores de busca concorrentes em bilhões de smartphones globalmente.\n\n### 📌 CONCLUSÃO\nO tribunal considerou esses arranjos como instrumentos ilegais de fechamento de mercado sob a Seção 2 do Sherman Act [Pág. 113 da Sentença].",
            "rejected": "MADA e RSA eram contratos que o Google fazia com fabricantes de celular Android para colocar seus aplicativos na tela e pagar comissão se eles não usassem outros buscadores.",
        },
        {
            "query": "Qual foi a conclusao final do Juiz Amit Mehta sobre o monopolio do Google sob a Secao 2 do Sherman Act?",
            "thought": "1. Identificar autoridade judiciaria: Juiz Federal Amit P. Mehta.\n2. Identificar disposicao legal: Secao 2 do Sherman Act (15 U.S.C. § 2).\n3. Mercados relevantes definidos: Servicos gerais de busca e anuncios de texto de busca geral.\n4. Veredito final: O Google e monopolista e agiu ilicitamente para manter seu monopolio atraves de acordos exclusivos de distribuicao.\n5. Ancorar citacao estrita: [Pag. 286 da Sentenca].",
            "chosen": "### ⚖️ EVIDÊNCIA FACTUAL [Pág. 286 da Sentença]\nEm seu pronunciamento final de mérito [Pág. 286], o Juiz Federal Amit Mehta proferiu a decisão definitiva dos autos:\n> *'O tribunal conclui que o Google é um monopolista e que tem agido para manter seu monopólio em violação à Seção 2 do Sherman Act.'*\n\n### 📑 ANÁLISE JURÍDICO-CONCORRENCIAL\nO tribunal estabeleceu que o Google detém mais de 89% de participação no mercado de buscas gerais e 88% em anúncios de texto de busca, sustentados por acordos verticais de exclusividade que fecharam mais de 50% de todos os canais de distribuição de buscas nos EUA.\n\n### 📌 CONCLUSÃO\nA sentença declarou formalmente a ilicitude das condutas do Google sob a Seção 2 da Lei Sherman [Pág. 286 da Sentença].",
            "rejected": "O juiz Amit Mehta disse no fim que o Google tem monopólio sim e que quebrou a lei antitruste com os acordos de busca que ele fez.",
        },
    ]

    for item in golden_cot_scenarios:
        cot_samples.append(
            {
                "instruction": "Você é um Perito Forense Antitruste no processo federal U.S. v. Google. Conduza um raciocínio probatório prévio e responda estritamente com ancoragem factual e citações de página.",
                "thought": item["thought"],
                "input": item["query"],
                "output": f"<pensamento_forense>\n{item['thought']}\n</pensamento_forense>\n\n{item['chosen']}",
            }
        )
        dpo_samples.append(
            {
                "prompt": item["query"],
                "chosen": item["chosen"],
                "rejected": item["rejected"],
            }
        )

    # Synthetic data augmentation over the real Silver-layer pages
    target_terms = [
        "isa",
        "rsa",
        "default",
        "scale",
        "query",
        "advertiser",
        "cpc",
        "auction",
        "browser",
        "market share",
    ]
    augmented_count = 0

    for page in pages:
        p_num = page["page"]
        content = page["content"]
        content_lower = content.lower()

        # Keep only highly probative excerpts
        matched = [t for t in target_terms if t in content_lower]
        if len(matched) >= 2:
            augmented_count += 1
            sample_text = content[:450].replace("\n", " ").strip()

            thought = (
                f"1. Analisar trecho da Página {p_num}.\n"
                f"2. Termos-chave identificados: {', '.join(matched)}.\n"
                f"3. Extrair relevância para o caso antitruste U.S. v. Google.\n"
                f"4. Ancorar citação estrita de página: [Pág. {p_num} da Sentença]."
            )

            answer = (
                f"### ⚖️ EVIDÊNCIA FACTUAL [Pág. {p_num} da Sentença]\n"
                f"Conforme detalhado nos autos [Pág. {p_num}], os registros processuais comprovam: '{sample_text}...'\n\n"
                f"### 📑 ANÁLISE JURÍDICO-CONCORRENCIAL\n"
                f"A prova documental aborda diretamente os mecanismos de {' e '.join(matched[:2])}, "
                f"evidenciando a dinâmica concorrencial analisada pelo Juiz Amit Mehta no processo federal.\n\n"
                f"### 📌 CONCLUSÃO\n"
                f"O trecho corrobora a tese acusatória de controle de mercado sob a Seção 2 do Sherman Act [Pág. {p_num} da Sentença]."
            )

            cot_samples.append(
                {
                    "instruction": "Atue como Perito Forense no caso U.S. v. Google e responda com análise probatória e citação estrita de página.",
                    "thought": thought,
                    "input": f"Com base na página {p_num} da sentença, qual a relevância probatória das evidências sobre {matched[0]}?",
                    "output": f"<pensamento_forense>\n{thought}\n</pensamento_forense>\n\n{answer}",
                }
            )

            dpo_samples.append(
                {
                    "prompt": f"Qual a relevância do trecho da página {p_num} sobre {matched[0]}?",
                    "chosen": answer,
                    "rejected": f"O trecho da página {p_num} fala sobre {matched[0]} no caso do Google.",
                }
            )

    random.shuffle(cot_samples)

    # Persist datasets
    with open(COT_TRAIN_FILE, "w", encoding="utf-8") as f:
        for s in cot_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(DPO_PREF_FILE, "w", encoding="utf-8") as f:
        for d in dpo_samples:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print("[OK] Data augmentation completed successfully!")
    print(f"     -> CoT dataset: {len(cot_samples)} reasoning samples in {COT_TRAIN_FILE.name}")
    print(f"     -> DPO dataset: {len(dpo_samples)} preference pairs in {DPO_PREF_FILE.name}")


if __name__ == "__main__":
    build_cot_dataset()
