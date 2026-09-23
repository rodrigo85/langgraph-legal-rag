"""
3-Generation Benchmark (Generation 0 vs Generation 1 vs Generation 2).
Compares three configurations of the SAME base model (no weight fine-tuning):
- Generation 0: base model (qwen2.5:7b-instruct-q3_K_M)
- Generation 1: Modelfile v1 - domain system prompt (antitrust-specialist)
- Generation 2: Modelfile v2 - structured Evidence/Analysis/Conclusion prompt (antitrust-specialist-v2)

Heuristic score: presence of a [Pag. N] citation, coverage of expected terms and
sectioned structure. Citations are checked for FORMAT only, not page validity
(the test context has no page numbers).
"""

import sys
import time
import re
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from src.config import OLLAMA_BASE_URL

console = Console()
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORT_MD_FILE = REPORTS_DIR / "training_evolution.md"
CHART_3GEN_SVG = REPORTS_DIR / "evolution_3_generations.svg"

TEST_PROMPTS = [
    {
        "id": "T1_ISA_APPLE",
        "question": "Qual era a porcentagem da receita que o Google repassava para a Apple no contrato ISA em 2016 e qual a sua motivacao concorrencial?",
        "expected_terms": ["36%", "isa", "apple", "safari", "sherman"],
        "context_doc": "In 2016, Apple and Google amended the ISA. Under the 2016 amendment, Google paid Apple 36% of net revenue from Safari queries. The agreement created a powerful disincentive for Apple to develop its own search engine."
    },
    {
        "id": "T2_NADELLA_TESTIMONY",
        "question": "O que Satya Nadella (Microsoft) testemunhou sobre a teoria do Google de que a concorrencia esta a 'apenas um clique de distancia'?",
        "expected_terms": ["satya nadella", "microsoft", "bing", "default", "escala"],
        "context_doc": "Microsoft CEO Satya Nadella testified that Google's claim that competition is 'one click away' is a complete fiction in practice. Without default status on Apple devices, Bing cannot achieve the query scale needed to compete."
    },
    {
        "id": "T3_ANDROID_MADA",
        "question": "O que sao os acordos MADA e RSA que o Google impunha aos fabricantes de smartphones Android?",
        "expected_terms": ["mada", "rsa", "google play", "pre-instalacao", "exclusividade"],
        "context_doc": "Google used Mobile Application Distribution Agreements (MADAs) to mandate preinstallation of the entire Google Suite, and Revenue Share Agreements (RSAs) to condition payments on device makers not preinstalling rival search engines."
    },
    {
        "id": "T4_SHERMAN_VERDICT",
        "question": "Qual foi a conclusao final do Juiz Amit Mehta sobre o monopolio do Google sob a Secao 2 do Sherman Act?",
        "expected_terms": ["secao 2", "sherman", "monopolio", "buscas gerais", "amit mehta"],
        "context_doc": "Judge Amit Mehta concluded that Google is a monopolist in general search services and general search text ads, and has maintained its monopoly through anticompetitive exclusive distribution agreements in violation of Section 2 of the Sherman Act."
    }
]


def query_model(model_name: str, prompt: str) -> Dict[str, Any]:
    start_time = time.time()
    llm = ChatOllama(
        model=model_name,
        temperature=0.0,
        base_url=OLLAMA_BASE_URL,
        num_predict=350,
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    latency = time.time() - start_time
    content = response.content

    # Rough estimate: ~1.3 tokens per whitespace-separated word
    tokens = len(content.split()) * 1.3
    tps = tokens / latency if latency > 0 else 0

    return {
        "text": content,
        "latency_sec": round(latency, 2),
        "tokens_per_sec": round(tps, 1),
    }


def evaluate_scores(text: str, expected_terms: List[str]) -> Dict[str, Any]:
    # 1. Page citation in the required format: [Pag. N] or [Pág. N] (format only, not validity)
    has_citation = bool(re.search(r"\[P[aá]g\.?\s*\d+[^\]]*\]", text, re.IGNORECASE))
    citation_score = 100 if has_citation else 10

    # 2. Coverage of expected domain terms
    text_lower = text.lower()
    matches = sum(1 for term in expected_terms if term.lower() in text_lower)
    term_score = int((matches / len(expected_terms)) * 100)

    # 3. Sectioned structure
    has_sections = ("###" in text) or ("**" in text and ":" in text)
    struct_score = 100 if has_sections else 40

    overall_score = int(0.4 * citation_score + 0.4 * term_score + 0.2 * struct_score)

    return {
        "has_citation": has_citation,
        "term_score": term_score,
        "citation_score": citation_score,
        "struct_score": struct_score,
        "overall_score": overall_score,
    }


def run_3_generations_benchmark():
    console.print(
        Panel.fit(
            "[bold cyan]3-GENERATION BENCHMARK: SAME BASE MODEL, DIFFERENT MODELFILES[/bold cyan]\n"
            "[white]Gen 0: Base model | Gen 1: Modelfile v1 | Gen 2: Modelfile v2 (structured prompt)\n"
            "Hardware: NVIDIA GeForce RTX 2060 (full VRAM offload)[/white]",
            border_style="cyan"
        )
    )

    models = [
        {"name": "qwen2.5:7b-instruct-q3_K_M", "label": "Gen 0: Base", "key": "gen0"},
        {"name": "antitrust-specialist", "label": "Gen 1: Modelfile v1", "key": "gen1"},
        {"name": "antitrust-specialist-v2", "label": "Gen 2: Modelfile v2", "key": "gen2"},
    ]

    all_results = []

    table = Table(title="3-Generation Scorecard", border_style="bright_blue")
    table.add_column("Scenario", style="cyan")
    table.add_column("Gen 0 (Base)", style="yellow")
    table.add_column("Gen 1 (Modelfile v1)", style="magenta")
    table.add_column("Gen 2 (Modelfile v2)", style="green")
    table.add_column("Gen 2 Citation (format)", style="bold green")
    table.add_column("Total Gain", style="bold blue")

    for case in TEST_PROMPTS:
        c_id = case["id"]
        q = case["question"]
        ctx = case["context_doc"]
        terms = case["expected_terms"]
        prompt = f"Contexto probatorio dos autos judiciais:\n{ctx}\n\nPergunta investigativa:\n{q}"

        console.print(f"\n[bold]Testing {c_id}:[/bold] '{q[:65]}...'")

        case_data = {"id": c_id, "question": q}

        for m in models:
            console.print(f"  [dim]-> Running {m['label']}...[/dim]")
            out = query_model(m["name"], prompt)
            ev = evaluate_scores(out["text"], terms)
            case_data[m["key"]] = {
                "score": ev["overall_score"],
                "has_citation": ev["has_citation"],
                "text": out["text"],
                "tps": out["tokens_per_sec"],
            }

        total_gain = case_data["gen2"]["score"] - case_data["gen0"]["score"]

        table.add_row(
            c_id,
            f"{case_data['gen0']['score']}/100",
            f"{case_data['gen1']['score']}/100",
            f"{case_data['gen2']['score']}/100",
            "Yes" if case_data["gen2"]["has_citation"] else "No",
            f"{total_gain:+d} pts",
        )

        all_results.append(case_data)

    console.print("\n")
    console.print(table)

    # Averages
    avg_gen0 = sum(r["gen0"]["score"] for r in all_results) / len(all_results)
    avg_gen1 = sum(r["gen1"]["score"] for r in all_results) / len(all_results)
    avg_gen2 = sum(r["gen2"]["score"] for r in all_results) / len(all_results)

    cit_gen0 = (sum(1 for r in all_results if r["gen0"]["has_citation"]) / len(all_results)) * 100
    cit_gen1 = (sum(1 for r in all_results if r["gen1"]["has_citation"]) / len(all_results)) * 100
    cit_gen2 = (sum(1 for r in all_results if r["gen2"]["has_citation"]) / len(all_results)) * 100

    generate_3gen_svg(avg_gen0, avg_gen1, avg_gen2)
    update_reports_markdown(all_results, avg_gen0, avg_gen1, avg_gen2, cit_gen0, cit_gen1, cit_gen2)


def generate_3gen_svg(g0: float, g1: float, g2: float):
    width = 750
    height = 360

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <rect width="{width}" height="{height}" fill="#0d1117" rx="10"/>

  <text x="{width/2}" y="36" fill="#58a6ff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="16" font-weight="bold" text-anchor="middle">
    Heuristic Score by Model Configuration (4 domain scenarios)
  </text>
  <text x="{width/2}" y="56" fill="#8b949e" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="12" text-anchor="middle">
    Same base model (Qwen 2.5 7B) | [Pag. N] citation format + expected terms + structure
  </text>

  <!-- Gen 0: Base -->
  <text x="80" y="115" fill="#e6edf3" font-size="13" font-weight="bold">Generation 0: Base model (Qwen 2.5 7B)</text>
  <rect x="80" y="125" width="450" height="32" fill="#21262d" rx="6"/>
  <rect x="80" y="125" width="{g0 * 4.5:.1f}" height="32" fill="#d29922" rx="6"/>
  <text x="{80 + g0 * 4.5 + 15}" y="146" fill="#d29922" font-size="14" font-weight="bold">{g0:.1f} / 100</text>

  <!-- Gen 1: Modelfile v1 -->
  <text x="80" y="195" fill="#e6edf3" font-size="13" font-weight="bold">Generation 1: Modelfile v1 - domain prompt (antitrust-specialist)</text>
  <rect x="80" y="205" width="450" height="32" fill="#21262d" rx="6"/>
  <rect x="80" y="205" width="{g1 * 4.5:.1f}" height="32" fill="#a371f7" rx="6"/>
  <text x="{80 + g1 * 4.5 + 15}" y="226" fill="#a371f7" font-size="14" font-weight="bold">{g1:.1f} / 100 ({(g1-g0):+.1f})</text>

  <!-- Gen 2: Modelfile v2 -->
  <text x="80" y="275" fill="#e6edf3" font-size="13" font-weight="bold">Generation 2: Modelfile v2 - structured prompt (antitrust-specialist-v2)</text>
  <rect x="80" y="285" width="450" height="32" fill="#21262d" rx="6"/>
  <rect x="80" y="285" width="{g2 * 4.5:.1f}" height="32" fill="#2ea043" rx="6"/>
  <text x="{80 + g2 * 4.5 + 15}" y="306" fill="#2ea043" font-size="14" font-weight="bold">{g2:.1f} / 100 ({(g2-g0):+.1f})</text>
</svg>"""

    with open(CHART_3GEN_SVG, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"[OK] 3-generation SVG chart written to: {CHART_3GEN_SVG.name}")


def update_reports_markdown(all_results, g0, g1, g2, c0, c1, c2):
    rows_md = []
    for r in all_results:
        gain = r["gen2"]["score"] - r["gen0"]["score"]
        cited = "Sim" if r["gen2"]["has_citation"] else "Não"
        rows_md.append(f"| **{r['id']}** | {r['gen0']['score']}/100 | {r['gen1']['score']}/100 | **{r['gen2']['score']}/100** | {cited} | **{gain:+d} pts** |")

    deep_dives = []
    for r in all_results:
        deep_dives.append(f"""
### 🔍 Cenário {r['id']}
**Pergunta:** *{r['question']}*

<details>
<summary><b>Respostas das 3 configurações (clique para expandir)</b></summary>

#### 🔴 Geração 0: Modelo Base (Nota {r['gen0']['score']}/100)
> {r['gen0']['text']}

#### 🟣 Geração 1: Modelfile v1 (Nota {r['gen1']['score']}/100)
> {r['gen1']['text']}

#### 🟢 Geração 2: Modelfile v2 (Nota {r['gen2']['score']}/100)
> {r['gen2']['text']}

**Auditoria:**
- Citação no formato `[Pág. N]` na Gen 2: **{'Sim' if r['gen2']['has_citation'] else 'Não'}** (formato, não validade da página)
- Evolução total: **{r['gen2']['score'] - r['gen0']['score']:+d} pontos**
</details>
""")

    report_text = f"""# 📈 Relatório de Evolução: 3 Configurações do Mesmo Modelo Base
### *U.S. v. Google LLC — Especialização de Domínio via Modelfile (Ollama, RTX 2060)*

Este relatório compara **três configurações do mesmo modelo base** (`qwen2.5:7b-instruct-q3_K_M`). **Não houve ajuste de pesos (fine-tuning)**: a especialização é feita por *system prompt* e parâmetros de inferência definidos em Modelfiles do Ollama.

1. **Geração 0 (Baseline)**: modelo base, sem system prompt.
2. **Geração 1 (Modelfile v1)**: system prompt de domínio exigindo citação `[Pág. N]` (`antitrust-specialist`).
3. **Geração 2 (Modelfile v2)**: prompt estruturado em Evidência / Análise / Conclusão, temperatura 0 (`antitrust-specialist-v2`).

---

## 📊 1. Quadro Comparativo

| Métrica | Geração 0 (Base) | Geração 1 (Modelfile v1) | Geração 2 (Modelfile v2) | Ganho Total |
| :--- | :---: | :---: | :---: | :---: |
| **Score heurístico médio (0-100)** | **{g0:.1f} pts** | **{g1:.1f} pts** | **{g2:.1f} pts** | **{(g2 - g0):+.1f} pontos ({((g2 - g0)/g0)*100:+.1f}%)** |
| **Respostas com citação no formato `[Pág. N]`** | **{c0:.0f}%** | **{c1:.0f}%** | **{c2:.0f}%** | **{c2 - c0:+.0f} p.p.** |

> **Como o score é calculado:** 40% presença de citação no formato `[Pág. N]`, 40% cobertura de termos esperados, 20% estrutura em seções. Amostra de 4 cenários, temperatura 0.

---

## 📉 2. Gráfico

![Score por configuração](./evolution_3_generations.svg)

---

## 📋 3. Scorecard por Cenário

| Cenário de Teste | Gen 0 (Base) | Gen 1 (Modelfile v1) | Gen 2 (Modelfile v2) | Citação Gen 2 (formato) | Ganho |
| :--- | :---: | :---: | :---: | :---: | :---: |
{chr(10).join(rows_md)}

---

## 🔬 4. Análise Qualitativa (Deep Dive)

{chr(10).join(deep_dives)}

---

## ⚠️ Limitações Conhecidas

1. **Citação checada no formato, não na validade**: o contexto fornecido nos testes não contém números de página, portanto os números citados pelos modelos são inventados. O ganho mede **aderência ao formato exigido pelo prompt**, não precisão de linhagem. A linhagem real de páginas é garantida no agente RAG (metadados de página dos chunks), não neste benchmark.
2. **Amostra pequena** (4 cenários) e score heurístico baseado em palavras-chave.
3. **Sem ajuste de pesos**: os datasets SFT/CoT/DPO em `data/training/` estão preparados para um fine-tuning LoRA futuro, ainda não executado.
"""

    with open(REPORT_MD_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"[OK] 3-generation report updated at: {REPORT_MD_FILE.name}")


if __name__ == "__main__":
    run_3_generations_benchmark()
