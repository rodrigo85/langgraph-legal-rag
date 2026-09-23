"""
Docket Loader & Temporal Registry API.
Fornece metadados temporais, marcos do julgamento e funcoes para Point-in-Time RAG.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCKETS_REGISTRY_PATH = PROJECT_ROOT / "data" / "metadata" / "dockets_registry.json"


def load_dockets_registry() -> Dict[str, Any]:
    """Carrega o registro oficial de dockets e marcos do julgamento."""
    if not DOCKETS_REGISTRY_PATH.exists():
        return {"case_info": {}, "milestones": []}
    with open(DOCKETS_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_milestones() -> List[Dict[str, Any]]:
    """Retorna todos os marcos cronologicos ordenados por data."""
    registry = load_dockets_registry()
    milestones = registry.get("milestones", [])
    return sorted(milestones, key=lambda m: m["filing_date"])


def get_milestone_by_id(milestone_id: str) -> Optional[Dict[str, Any]]:
    """Retorna um marco especifico pelo ID."""
    milestones = get_all_milestones()
    for m in milestones:
        if m["id"] == milestone_id:
            return m
    return None


def get_active_milestones_as_of(as_of_date: str) -> List[Dict[str, Any]]:
    """
    Retorna todos os marcos que ja haviam ocorrido ate a data especificada (YYYY-MM-DD).
    Garante a integridade historica e previne Lookahead Bias.
    """
    milestones = get_all_milestones()
    return [m for m in milestones if m["filing_date"] <= as_of_date]


def get_latest_milestone_as_of(as_of_date: str) -> Optional[Dict[str, Any]]:
    """Retorna o marco mais recente ocorrido ate a data especificada."""
    active = get_active_milestones_as_of(as_of_date)
    return active[-1] if active else None


if __name__ == "__main__":
    registry = load_dockets_registry()
    print(f"[OK] Dockets carregados: {len(registry.get('milestones', []))} marcos mapeados.")
    sample_date = "2023-09-26"
    active = get_active_milestones_as_of(sample_date)
    print(f"[*] Marcos ativos em {sample_date}: {len(active)}")
    for m in active:
        print(f"    - [{m['filing_date']}] {m['title']}")
