"""
SFT / Instruction-Tuning Dataset Generator.
Transforms raw and structured Silver-layer data (Doc 1033) into
(Instruction, Context, Forensic Reasoning, Answer) samples, prepared for a future
LoRA fine-tune. No model weights have been trained on this dataset yet.
"""

import json
import random
from typing import Any, Dict, List

from legal_rag.config import SILVER_CORPUS_JSONL, TRAINING_DATA_DIR

TRAINING_DIR = TRAINING_DATA_DIR
TRAIN_FILE = TRAINING_DIR / "train.jsonl"
EVAL_FILE = TRAINING_DIR / "eval.jsonl"
META_FILE = TRAINING_DIR / "dataset_metadata.json"


# Instruction templates framing the Antitrust Forensic Expert role
INSTRUCTION_TEMPLATES = [
    "Atue como um Perito Forense e analise as clausulas do acordo antitruste no texto judicial a seguir.",
    "Com base estrita nas evidencias documentais do caso U.S. v. Google, responda a questao com citacao mandatoria de paginas.",
    "Examine as provas do processo antitruste e identifique o impacto concorrencial da conduta descrita.",
    "Realize uma analise juridica e financeira dos acordos de compartilhamento de receita citados na sentenca judicial.",
]


def extract_key_excerpts() -> List[Dict[str, Any]]:
    """
    Identifies high-factual-impact pages in the Silver layer
    (e.g. internal e-mails, Apple-Google agreements, Satya Nadella and Sundar Pichai testimony).
    """
    if not SILVER_CORPUS_JSONL.exists():
        raise FileNotFoundError(f"Silver file not found at: {SILVER_CORPUS_JSONL}")

    records = []
    with open(SILVER_CORPUS_JSONL, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Keep pages rich in contractual and evidentiary terms
    target_terms = ["isa", "rsa", "revenue share", "default", "nadella", "pichai", "safari", "sherman", "android"]
    high_impact_pages = []

    for rec in records:
        content_lower = rec["content"].lower()
        score = sum(1 for term in target_terms if term in content_lower)
        if score >= 2:
            high_impact_pages.append(rec)

    print(f"[*] Identified {len(high_impact_pages)} high-evidentiary-density pages for the dataset.")
    return high_impact_pages


def generate_sft_dataset() -> None:
    """
    Generates samples in the standard Alpaca/ChatML format:
    {
       "instruction": ...,
       "input": ...,
       "output": ...
    }
    """
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    pages = extract_key_excerpts()

    dataset_samples = []

    # Hand-curated scenarios with in-depth forensic reasoning
    sft_scenarios = [
        {
            "query": "Qual era a taxa de revenue share paga pelo Google a Apple pelo acordo ISA em 2016 e como isso impactava o mercado?",
            "page_match": 114,
            "response": "Conforme registrado na Sentenca Judicial [Pag. 114], no termo aditivo de 2016 do Information Services Agreement (ISA), o Google concordou em repassar a Apple 36% da receita liquida de publicidade gerada atraves das buscas no Safari. Essa clausula criava um forte desincentivo financeiro para que a Apple desenvolvesse ou adotasse um buscador concorrente, consolidando o monopolio de distribuicao padrao sob a Secao 2 do Sherman Act.",
        },
        {
            "query": "O que Satya Nadella testemunhou sob juramento sobre o Bing conseguir competir com o Google no iPhone?",
            "page_match": 245,
            "response": "Em depoimento sob juramento citado na sentenca [Pag. 245], o CEO da Microsoft Satya Nadella afirmou categoricamente que, sem a distribuicao padrao no Safari da Apple, o Bing jamais conseguiria escala suficiente para competir. Nadella declarou que o argumento do Google de que a concorrencia esta a 'apenas um clique de distancia' e uma falacia na pratica corporativa, pois os usuarios raramente alteram o mecanismo de busca pre-instalado.",
        },
        {
            "query": "Como funcionavam os acordos Mobile Application Distribution Agreement (MADA) e RSA no ecossistema Android?",
            "page_match": 113,
            "response": "De acordo com as determinacoes judiciais [Pag. 113], o Google condicionava o licenciamento do Google Play Store (atraves do MADA) a pre-instalacao obrigatoria de todo o conjunto de aplicativos proprietarios do Google (Google Suite), alem de firmar Revenue Sharing Agreements (RSAs) que concediam porcentagens de faturamento de anuncios aos fabricantes e operadoras apenas se nenhum buscador concorrente fosse pre-instalado no dispositivo.",
        },
        {
            "query": "Qual foi a conclusao juridica final do Juiz Amit Mehta sobre o mercado relevante de buscas gerais em texto?",
            "page_match": 286,
            "response": "Na decisao final de merito [Pag. 286], o tribunal concluiu que o Google e detentor de monopolio no mercado relevante de servicos gerais de busca e anuncios de texto de busca geral (general search text ads), tendo mantido seu poder monopolista de forma anticompetitiva atraves de acordos exclusivos de distribuicao, em violacao direta a Secao 2 do Sherman Act.",
        },
        {
            "query": "Qual o valor financeiro estimado que o Google desembolsou em acordos de distribuicao de busca em 2021?",
            "page_match": 115,
            "response": "Conforme evidenciado nos relatorios financeiros desclassificados durante o julgamento [Pag. 115], o Google pagou mais de US$ 26 bilhoes apenas no ano de 2021 para garantir o status de mecanismo de busca padrao em navegadores e dispositivos parceiros, sendo a maior fatia destinada a Apple pelo contrato ISA.",
        },
    ]

    for scenario in sft_scenarios:
        instruction = random.choice(INSTRUCTION_TEMPLATES)
        dataset_samples.append({"instruction": instruction, "input": scenario["query"], "output": scenario["response"]})

    # Expand with variations built from the identified pages
    for p in pages[:45]:
        page_num = p["page"]
        text_snippet = p["content"][:400].replace("\n", " ")
        dataset_samples.append(
            {
                "instruction": "Atue como perito judicial no caso antitruste U.S. v. Google e responda com citacao estrita de fontes.",
                "input": f"Com base na pagina {page_num} da sentenca, sintetize as evidencias contratuais discutidas neste trecho: '{text_snippet[:150]}...'",
                "output": f"Segundo a analise do tribunal registrada na [Pag. {page_num} da Sentenca], as provas desclassificadas comprovam que: {text_snippet}. Este fato corrobora o controle exercido pelo Google sobre os canais primarios de distribuicao.",
            }
        )

    random.shuffle(dataset_samples)

    # 80% train / 20% eval split
    split_idx = int(len(dataset_samples) * 0.8)
    train_data = dataset_samples[:split_idx]
    eval_data = dataset_samples[split_idx:]

    with open(TRAIN_FILE, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(EVAL_FILE, "w", encoding="utf-8") as f:
        for item in eval_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    metadata = {
        "dataset_name": "us_v_google_antitrust_sft",
        "total_samples": len(dataset_samples),
        "train_samples": len(train_data),
        "eval_samples": len(eval_data),
        "format": "Alpaca / ChatML JSONL",
        "primary_source": "U.S. v. Google LLC (Doc 1033 - 286 pages)",
    }

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("[OK] SFT dataset generated successfully!")
    print(f"     -> Train: {len(train_data)} samples in {TRAIN_FILE.name}")
    print(f"     -> Eval: {len(eval_data)} samples in {EVAL_FILE.name}")
    print(f"     -> Metadata written to {META_FILE.name}")


if __name__ == "__main__":
    generate_sft_dataset()
