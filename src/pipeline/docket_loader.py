"""
Docket Loader & Temporal Registry API.
Provides temporal metadata, trial milestones and helpers for Point-in-Time RAG.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCKETS_REGISTRY_PATH = PROJECT_ROOT / "data" / "metadata" / "dockets_registry.json"


def load_dockets_registry() -> Dict[str, Any]:
    """Loads the official registry of dockets and trial milestones."""
    if not DOCKETS_REGISTRY_PATH.exists():
        return {"case_info": {}, "milestones": []}
    with open(DOCKETS_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_milestones() -> List[Dict[str, Any]]:
    """Returns all chronological milestones sorted by date."""
    registry = load_dockets_registry()
    milestones = registry.get("milestones", [])
    return sorted(milestones, key=lambda m: m["filing_date"])


def get_milestone_by_id(milestone_id: str) -> Optional[Dict[str, Any]]:
    """Returns a specific milestone by ID."""
    milestones = get_all_milestones()
    for m in milestones:
        if m["id"] == milestone_id:
            return m
    return None


def get_active_milestones_as_of(as_of_date: str) -> List[Dict[str, Any]]:
    """
    Returns all milestones that had already occurred by the given date (YYYY-MM-DD).
    Preserves historical integrity and prevents lookahead bias.
    """
    milestones = get_all_milestones()
    return [m for m in milestones if m["filing_date"] <= as_of_date]


def get_latest_milestone_as_of(as_of_date: str) -> Optional[Dict[str, Any]]:
    """Returns the most recent milestone that occurred by the given date."""
    active = get_active_milestones_as_of(as_of_date)
    return active[-1] if active else None


if __name__ == "__main__":
    registry = load_dockets_registry()
    print(f"[OK] Dockets loaded: {len(registry.get('milestones', []))} milestones mapped.")
    sample_date = "2023-09-26"
    active = get_active_milestones_as_of(sample_date)
    print(f"[*] Active milestones as of {sample_date}: {len(active)}")
    for m in active:
        print(f"    - [{m['filing_date']}] {m['title']}")
