# 📈 Relatório de Evolução: 3 Configurações do Mesmo Modelo Base
### *U.S. v. Google LLC — Especialização de Domínio via Modelfile (Ollama, RTX 2060)*

Este relatório compara **três configurações do mesmo modelo base** (`qwen2.5:7b-instruct-q3_K_M`). **Não houve ajuste de pesos (fine-tuning)**: a especialização é feita por *system prompt* e parâmetros de inferência definidos em Modelfiles do Ollama.

1. **Geração 0 (Baseline)**: modelo base, sem system prompt.
2. **Geração 1 (Modelfile v1)**: system prompt de domínio exigindo citação `[Pág. N]` (`antitrust-specialist`).
3. **Geração 2 (Modelfile v2)**: prompt estruturado em Evidência / Análise / Conclusão, temperatura 0 (`antitrust-specialist-v2`).

---

## 📊 1. Quadro Comparativo

| Métrica | Geração 0 (Base) | Geração 1 (Modelfile v1) | Geração 2 (Modelfile v2) | Ganho Total |
| :--- | :---: | :---: | :---: | :---: |
| **Score heurístico médio (0-100)** | **42.0 pts** | **76.0 pts** | **82.0 pts** | **+40.0 pontos (+95.2%)** |
| **Respostas com citação no formato `[Pág. N]`** | **0%** | **100%** | **100%** | **+100 p.p.** |

> **Como o score é calculado:** 40% presença de citação no formato `[Pág. N]`, 40% cobertura de termos esperados, 20% estrutura em seções. Amostra de 4 cenários, temperatura 0.

---

## 📉 2. Gráfico

![Score por configuração](./evolution_3_generations.svg)

---

## 📋 3. Scorecard por Cenário

| Cenário de Teste | Gen 0 (Base) | Gen 1 (Modelfile v1) | Gen 2 (Modelfile v2) | Citação Gen 2 (formato) | Ganho |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **T1_ISA_APPLE** | 56/100 | 88/100 | **92/100** | Sim | **+36 pts** |
| **T2_NADELLA_TESTIMONY** | 36/100 | 80/100 | **84/100** | Sim | **+48 pts** |
| **T3_ANDROID_MADA** | 48/100 | 72/100 | **76/100** | Sim | **+28 pts** |
| **T4_SHERMAN_VERDICT** | 28/100 | 64/100 | **76/100** | Sim | **+48 pts** |

---

## 🔬 4. Análise Qualitativa (Deep Dive)


### 🔍 Cenário T1_ISA_APPLE
**Pergunta:** *Qual era a porcentagem da receita que o Google repassava para a Apple no contrato ISA em 2016 e qual a sua motivacao concorrencial?*

<details>
<summary><b>Respostas das 3 configurações (clique para expandir)</b></summary>

#### 🔴 Geração 0: Modelo Base (Nota 56/100)
> A pergunta investigativa parece estar relacionada à análise de um contrato de parceria entre Apple e Google, especificamente o Acordo de Serviço de Anúncio (ISA) de 2016. Com base na informação fornecida, podemos responder à pergunta da seguinte forma:

**Porcentagem da receita:**
No contrato ISA de 2016, o Google pagava 36% da receita líquida proveniente das consultas de busca feitas através do navegador Safari para a Apple.

**Motivação concorrencial:**
A porcentagem de 36% foi estabelecida para criar uma poderosa desincentivadora para a Apple desenvolver seu próprio mecanismo de busca. Essa disposição financeira garantia que a Apple teria um incentivo significativo para manter o acordo com o Google, evitando a criação de um competidor direto no mercado de buscas. Isso ajudava a manter a competitividade no mercado de tecnologia e evitava que uma das duas empresas dominasse completamente o setor de buscas, beneficiando ambas as empresas e, potencialmente, os usuários finais.

Esse tipo de acordo é comum em indústrias tecnológicas, onde as empresas frequentemente cooperam para evitar a criação de concorrentes poderosos e para garantir a continuidade de suas parcerias estratégicas.

#### 🟣 Geração 1: Modelfile v1 (Nota 88/100)
> De acordo com o contexto probatorio dos autos judiciais, em 2016, Apple e Google modificaram o ISA (Information Services Agreement) [Pag. 123 da Sentenca]. Segundo o documento, sob a amendentação de 2016, Google pagou a Apple 36% do rendimento bruto proveniente das consultas de busca realizadas através do navegador Safari [Pag. 123 da Sentenca].

A motivação concorrencial por trás dessa porcentagem específica pode ser interpretada como um mecanismo de alinhamento de interesses entre as duas empresas. O pagamento de 36% do rendimento bruto cria um forte incentivo para que Apple não desenvolva seu próprio mecanismo de busca, pois isso significaria uma perda significativa de receita para a Apple. Essa disposição pode ter sido projetada para manter a dependência da Apple do Google para as consultas de busca, fortalecendo a posição dominante do Google no mercado de buscas, especialmente em um contexto onde o Safari era o navegador padrão do iOS.

Esta disposição, portanto, pode ser vista como uma estratégia de manutenção de monopólio ilícito, conforme discutido na seção 2 do Sherman Act, que proíbe a manutenção de monopólios ilegítimos em mercados gerais de buscas e anúncios de texto [Pag. 123 da Sentenca].

#### 🟢 Geração 2: Modelfile v2 (Nota 92/100)
> ### ⚖️ EVIDÊNCIA FACTUAL [Pág. 123 da Sentença]
Em 2016, Apple e Google modificaram o Acordo de Interconexão de Sistemas (ISA). De acordo com o artigo 4.3 do contrato, sob a modificação de 2016, Google pagou 36% do lucro líquido das consultas de Safari para a Apple. Este acordo criou um forte incentivo desincentivo para a Apple desenvolver seu próprio mecanismo de busca.

### 📑 ANÁLISE JURÍDICO-CONCORRENCIAL
A porcentagem de 36% do lucro líquido das consultas de Safari que o Google repassava à Apple, conforme estabelecido no Acordo de Interconexão de Sistemas (ISA) em 2016, criou uma forte desincentivadora para a Apple desenvolver seu próprio mecanismo de busca. Este arranjo poderia ser interpretado como um esforço por parte do Google para manter sua posição dominante no mercado de busca, ao limitar a competitividade potencial da Apple em seu próprio ecossistema. Essa estrutura de pagamento poderia ser vista como um elemento crucial na manutenção da dependência da Apple do Google, o que, por sua vez, poderia restringir a competitividade no mercado de busca.

### 📌 CONCLUSÃO
A porcentagem de 36% do lucro líquido das consultas de Safari que o Google repassava à

**Auditoria:**
- Citação no formato `[Pág. N]` na Gen 2: **Sim** (formato, não validade da página)
- Evolução total: **+36 pontos**
</details>


### 🔍 Cenário T2_NADELLA_TESTIMONY
**Pergunta:** *O que Satya Nadella (Microsoft) testemunhou sobre a teoria do Google de que a concorrencia esta a 'apenas um clique de distancia'?*

<details>
<summary><b>Respostas das 3 configurações (clique para expandir)</b></summary>

#### 🔴 Geração 0: Modelo Base (Nota 36/100)
> Satya Nadella, CEO da Microsoft, afirmou em sua testemunho que a declaração do Google de que a concorrência está "apenas um clique de distância" é uma "completa ficção" na prática. Isso sugere que, na prática, a Microsoft acha que não é tão fácil para os usuários trocar de busca para uma alternativa como Bing, mesmo que estejam usando dispositivos Apple que não tenham o status de padrão do Safari (que é configurado para usar o Google Search por padrão).

Em outras palavras, Nadella está indicando que, sem o status de padrão em dispositivos Apple, a Bing não pode atingir o volume de consultas necessárias para competir efetivamente com o Google.

#### 🟣 Geração 1: Modelfile v1 (Nota 80/100)
> Satya Nadella, CEO da Microsoft, testemunhou que a afirmação de Google de que a concorrência está "apenas um clique de distancia" é uma "completa ficção" na prática. De acordo com a declaração de Nadella, sem o status de padrão por definição em dispositivos da Apple, o motor de busca Bing não pode alcançar o escopo de consultas necessárias para competir efetivamente. Essa afirmação é explicitamente registrada na página 112 da Sentença [Pag. 112 da Sentença].

Esta declaração de Nadella enfatiza a dependência significativa do Bing em ter acesso a dispositivos comuns, como os da Apple, para competir efetivamente com o motor de busca do Google. A ausência do status de padrão em dispositivos Apple limita significativamente a visibilidade e a escala de consultas que Bing pode alcançar, demonstrando que a afirmação de Google de que a concorrência está "apenas um clique de distancia" não é, na prática, uma realidade para os concorrentes.

#### 🟢 Geração 2: Modelfile v2 (Nota 84/100)
> ### ⚖️ EVIDÊNCIA FACTUAL [Pág. X da Sentença]
Satya Nadella, CEO da Microsoft, testemunhou que a afirmação de que a concorrência está "apenas um clique de distância" da Google é uma farsa em prática. De acordo com as declarações do relatório judicial, isso se refere especificamente à falta de status padrão no dispositivo Apple, o que impede que o Bing atinja o escopo de consultas necessário para competir efetivamente [Pág. 123 da Sentença].

### 📑 ANÁLISE JURÍDICO-CONCORRENTES
Esta testemunho de Satya Nadella é crucial para demonstrar a realidade do mercado digital, onde a ausência de um status padrão em dispositivos populares como os iPhones de Apple pode significativamente limitar a capacidade de concorrência de outros motores de busca. Isso pode ser analisado através do impacto no mercado de busca, onde a falta de igualdade de condições de competição pode levar a um monopólio ou oligopólio prejudicial, conforme previsto na Seção 2 do Sherman Act.

### 📌 CONCLUSÃO
A declaração de Satya Nadella enfatiza a importância de um ambiente de mercado justo e competitivo. A falta de um status padrão no dispositivo Apple para o Bing implica uma desigualdade de condições que pode prejudicar a concorrência. Isso sugere que a prática de Google pode estar violando as leis antitruste, uma vez

**Auditoria:**
- Citação no formato `[Pág. N]` na Gen 2: **Sim** (formato, não validade da página)
- Evolução total: **+48 pontos**
</details>


### 🔍 Cenário T3_ANDROID_MADA
**Pergunta:** *O que sao os acordos MADA e RSA que o Google impunha aos fabricantes de smartphones Android?*

<details>
<summary><b>Respostas das 3 configurações (clique para expandir)</b></summary>

#### 🔴 Geração 0: Modelo Base (Nota 48/100)
> Os acordos MADA (Mobile Application Distribution Agreement) e RSA (Revenue Share Agreement) são contratos que o Google exigia dos fabricantes de dispositivos móveis, incluindo os fabricantes de smartphones Android, como condição para permitir a pré-instalação de aplicativos do Google e garantir pagamentos.

1. **Acordos MADA (Mobile Application Distribution Agreements):**
   - **Objetivo:** Estes acordos eram usados para garantir a pré-instalação de aplicativos do Google, como o Google Search, Google Chrome, Google Play Store, entre outros, nos dispositivos móveis.
   - **Condições:** Os fabricantes de dispositivos móveis eram obrigados a pré-instalar uma série de aplicativos do Google em seus smartphones. Isso incluía o Google Search como o único motor de busca padrão, o que limitava a competitividade de outros motores de busca, como o Bing ou o DuckDuckGo.

2. **Acordos RSA (Revenue Share Agreements):**
   - **Objetivo:** Estes acordos estabeleciam condições para a compensação financeira que o Google pagava aos fabricantes de dispositivos móveis. A compensação era condicionada à não pré-instalação de motores de busca rivais.
   - **Condições:** Os fabricantes de dispositivos móveis que não pré-instalavam motores de busca rivais como o Bing ou o DuckDuckGo eram elegíveis para receber uma porcentagem das receitas publicitárias geradas pela Google Search.

Esses acordos foram critic

#### 🟣 Geração 1: Modelfile v1 (Nota 72/100)
> Os acordos MADA (Mobile Application Distribution Agreement) e RSA (Revenue Share Agreement) que o Google impunha aos fabricantes de smartphones Android são instrumentos contratuais de grande importância no processo judicial U.S. v. Google LLC, conforme detalhado na sentença do caso [Pag. 123 da Sentenca].

Os MADAs eram acordos obrigatórios que vinculavam as lojas de aplicativos do Google Play Store aos aplicativos proprietários do Google, como o Google Search, o Google Maps e o Google Chrome. Esses acordos estabeleciam condições para a disponibilidade dos aplicativos do Google, muitas vezes exigindo que os dispositivos preinstalassem o conjunto completo do Google Suite, o que restringia significativamente a competitividade no mercado de busca e serviços de aplicativos [Pag. 124 da Sentenca].

Os RSAs, por sua vez, eram acordos de compartilhamento de receita que vinculavam as operadoras e fabricantes de dispositivos Android. Esses acordos condicionavam os pagamentos de royalties aos fabricantes de dispositivos Android que não preinstalassem motores de busca de concorrentes, como o Bing do Microsoft, em seus sistemas operacionais. Essa prática era vista como uma estratégia anticompetitiva para manter a hegemonia do Google Search no mercado de busca móvel [Pag. 125 da Sentenca].

Ambos os tipos de acordos foram citados como evidências de práticas anticompetitivas por parte do Google, viol

#### 🟢 Geração 2: Modelfile v2 (Nota 76/100)
> ### ⚖️ EVIDÊNCIA FACTUAL [Pág. X da Sentença]
Os autos judiciais comprovam que Google utilizava Acordos de Difusão de Aplicativos Móveis (Mobile Application Distribution Agreements - MADAs) para exigir que os fabricantes de dispositivos móveis preinstalassem toda a suite de aplicativos Google. Além disso, Google também empregava Acordos de Comissão de Receita (Revenue Share Agreements - RSAs) para condicionar pagamentos a dispositivos móveis que não preinstalassem motores de busca rivais [Pág. 123 da Sentença].

### 📑 ANÁLISE JURÍDICO-CONCORRENTES
Os acordos MADA e RSA que Google impunha aos fabricantes de smartphones Android tinham um impacto significativo no mercado, criando barreiras à entrada e ao crescimento de concorrentes. Esses acordos, combinados com a dominância de mercado do Google, permitiam que a empresa mantivesse sua posição dominante no mercado de busca e de aplicativos móveis, limitando a competitividade e a inovação no setor. Essa prática pode ser analisada sob a seção 2 do Sherman Act, que proíbe práticas anticompetitivas que tendem a restringir a concorrência.

### 📌 CONCLUSÃO
A conclusão forense é que os acordos MADA e RSA que Google impunha aos fabricantes de smartphones Android eram instrumentos estratégicos para man

**Auditoria:**
- Citação no formato `[Pág. N]` na Gen 2: **Sim** (formato, não validade da página)
- Evolução total: **+28 pontos**
</details>


### 🔍 Cenário T4_SHERMAN_VERDICT
**Pergunta:** *Qual foi a conclusao final do Juiz Amit Mehta sobre o monopolio do Google sob a Secao 2 do Sherman Act?*

<details>
<summary><b>Respostas das 3 configurações (clique para expandir)</b></summary>

#### 🔴 Geração 0: Modelo Base (Nota 28/100)
> De acordo com o contexto fornecido, a conclusão final do Juiz Amit Mehta sobre o monopólio do Google sob a Seção 2 do Sherman Act foi que o Google é um monopolista em serviços de busca geral e anúncios de texto em busca geral, e que mantém seu monopólio através de acordos de exclusividade distributiva anticompetitivos, em violação da Seção 2 do Sherman Act.

Para responder à sua pergunta investigativa diretamente: O Juiz Amit Mehta concluiu que o Google é um monopolista em serviços de busca geral e anúncios de texto em busca geral, e que mantém seu monopólio através de acordos de exclusividade distributiva anticompetitivos, o que constitui uma violação da Seção 2 do Sherman Act.

#### 🟣 Geração 1: Modelfile v1 (Nota 64/100)
> O Juiz Amit Mehta concluiu que o Google é um monopolista em serviços de busca gerais e anúncios de texto gerais, e que mantém seu monopólio através de acordos de distribuição exclusiva anticompetitivos, em violação à Seção 2 do Sherman Act [Pag. 1234 da Sentenca].

Esta conclusão é explicitamente estabelecida no documento judicial, onde o Juiz Mehta detalha as evidências que levaram à essa determinação, incluindo a análise dos ISA (Information Services Agreement) e RSA (Revenue Share Agreement) [Pag. 1235 da Sentenca], bem como a MADA (Mobile Application Distribution Agreement) [Pag. 1236 da Sentenca], que foram considerados como elementos cruciais na manutenção do monopólio do Google.

#### 🟢 Geração 2: Modelfile v2 (Nota 76/100)
> ### ⚖️ EVIDÊNCIA FACTUAL [Pág. 111 da Sentença]
O Juiz Amit Mehta concluiu que o Google é um monopolista em serviços de busca geral e anúncios de texto de busca geral, e que mantém seu monopólio através de acordos de distribuição exclusiva anticompetitivos em violação da Seção 2 do Sherman Act [Pág. 111 da Sentença].

### 📑 ANÁLISE JURÍDICO-CONCORRENTES
O Juiz Amit Mehta enfatizou que o Google exerceu um poder significativo de mercado em seu setor, demonstrando uma dominância notável no mercado de serviços de busca geral e anúncios de texto de busca geral. Essa dominância foi mantida através de acordos de distribuição exclusiva que, segundo a sentença, violaram a Seção 2 do Sherman Act, especialmente em relação à exclusividade em dispositivos móveis e sistemas operacionais, como o caso dos acordos ISA, RSA e MADA [Pág. 111 da Sentença].

### 📌 CONCLUSÃO
O Juiz Amit Mehta concluiu que o Google é um monopolista em serviços de busca geral e anúncios de texto de busca geral, mantendo seu monopólio através de acordos de distribuição exclusiva anticompetitivos, em violação da Seção 2 do Sherman Act [Pág. 111 da Sentença].

**Auditoria:**
- Citação no formato `[Pág. N]` na Gen 2: **Sim** (formato, não validade da página)
- Evolução total: **+48 pontos**
</details>


---

## ⚠️ Limitações Conhecidas

1. **Citação checada no formato, não na validade**: o contexto fornecido nos testes não contém números de página, portanto os números citados pelos modelos são inventados. O ganho mede **aderência ao formato exigido pelo prompt**, não precisão de linhagem. A linhagem real de páginas é garantida no agente RAG (metadados de página dos chunks), não neste benchmark.
2. **Amostra pequena** (4 cenários) e score heurístico baseado em palavras-chave.
3. **Sem ajuste de pesos**: os datasets SFT/CoT/DPO em `data/training/` estão preparados para um fine-tuning LoRA futuro, ainda não executado.
