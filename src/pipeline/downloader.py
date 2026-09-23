"""
Camada Bronze - Ingestao Bruta de Dados.
Modulo responsavel pelo download idempotente e validacao de integridade
do documento judicial oficial (Doc 1033) a partir do RECAP/CourtListener.
"""

import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import OPINION_PDF_PATH

# URL autenticada no RECAP/CourtListener
OPINION_PDF_URL = "https://storage.courtlistener.com/recap/gov.uscourts.dcd.223205/gov.uscourts.dcd.223205.1033.0_5.pdf"


def download_court_opinion(url: str = OPINION_PDF_URL, target_path: Path = OPINION_PDF_PATH) -> Path:
    """
    Realiza o download idempotente do arquivo bruto para a camada Bronze.
    Valida tamanho de arquivo e assinatura %PDF-.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and target_path.stat().st_size > 1_000_000:
        size_mb = target_path.stat().st_size / (1024 * 1024)
        print(f"[BRONZE] Arquivo bruto ja presente em: {target_path.name} ({size_mb:.2f} MB)")
        return target_path

    print(f"[BRONZE] Baixando documento judicial de: {url}")
    print(f"[BRONZE] Salvando em: {target_path}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DataEngineeringPipeline/1.0"
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(target_path, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 64 * 1024

        while True:
            buffer = response.read(chunk_size)
            if not buffer:
                break
            downloaded += len(buffer)
            out_file.write(buffer)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                mb = downloaded / (1024 * 1024)
                sys.stdout.write(f"\r[BRONZE] Progresso: {percent:.1f}% ({mb:.2f} MB)")
                sys.stdout.flush()

    print("\n[BRONZE] Download concluido.")

    # Validacao de Assinatura Magica de Formato
    with open(target_path, "rb") as f:
        header = f.read(5)
        if header != b"%PDF-":
            raise ValueError(f"[ERRO DE DADOS] Arquivo corrompido ou invalido. Cabecalho: {header}")

    size_mb = target_path.stat().st_size / (1024 * 1024)
    print(f"[BRONZE] Validacao de integridade OK ({size_mb:.2f} MB).")
    return target_path


if __name__ == "__main__":
    download_court_opinion()

