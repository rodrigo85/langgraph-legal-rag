"""
Script para download automático dos documentos oficiais do processo antitruste:
U.S. v. Google LLC (Caso 1:20-cv-03010-APM)
Documento 1033: Sentença de Mérito do Juiz Amit P. Mehta (286 páginas).
"""

import sys
import os
import urllib.request
from pathlib import Path

# URL pública e oficial armazenada no RECAP/CourtListener
OPINION_PDF_URL = "https://storage.courtlistener.com/recap/gov.uscourts.dcd.223205/gov.uscourts.dcd.223205.1033.0_5.pdf"

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
TARGET_FILE = DATA_DIR / "us_v_google_opinion_1033.pdf"


def download_court_opinion(url: str = OPINION_PDF_URL, target_path: Path = TARGET_FILE) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and target_path.stat().st_size > 1_000_000:
        size_mb = target_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Documento ja existe em: {target_path} ({size_mb:.2f} MB)")
        return target_path

    print(f"[*] Baixando a Decisao Judicial do Juiz Amit Mehta...")
    print(f"[*] Fonte: {url}")
    print(f"[*] Destino: {target_path}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AntitrustResearchAgent/1.0"
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
                sys.stdout.write(f"\rBaixando: {percent:.1f}% ({mb:.2f} MB)")
                sys.stdout.flush()

    print("\n[OK] Download concluido com sucesso!")
    
    # Validar se o arquivo realmente comeca com %PDF-
    with open(target_path, "rb") as f:
        header = f.read(5)
        if header != b"%PDF-":
            raise ValueError(f"Arquivo baixado nao parece ser um PDF valido. Cabecalho: {header}")

    size_mb = target_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Arquivo PDF autenticado e validado ({size_mb:.2f} MB).")
    return target_path


if __name__ == "__main__":
    download_court_opinion()
