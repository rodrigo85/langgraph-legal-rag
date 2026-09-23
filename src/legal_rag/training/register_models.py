"""
Registers the domain-specialized models in Ollama (Modelfile specialization).

NOTE: this script does NOT fine-tune weights. Each Modelfile starts from the base
model `qwen2.5:7b-instruct-q3_K_M` and only defines:
  - a domain SYSTEM prompt (forensic persona, [Pag. N] citation format)
  - inference parameters (temperature, top_p, top_k, num_ctx, num_gpu)

Registered models:
  - antitrust-specialist     (Modelfile)    -> Generation 1: domain system prompt
  - antitrust-specialist-v2  (Modelfile.v2) -> Generation 2: structured Evidence/Analysis/Conclusion prompt

The datasets in data/training/ (SFT, CoT and DPO pairs) are prepared for a future
LoRA fine-tune and have not been used to train weights yet.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

TRAINING_SRC_DIR = Path(__file__).resolve().parent

MODELS = [
    ("antitrust-specialist", TRAINING_SRC_DIR / "Modelfile"),
    ("antitrust-specialist-v2", TRAINING_SRC_DIR / "Modelfile.v2"),
]


def find_ollama_executable() -> str:
    """Finds the Ollama binary on PATH, falling back to the default Windows install location."""
    found = shutil.which("ollama")
    if found:
        return found
    windows_default = os.path.expandvars(r"$LOCALAPPDATA\Programs\Ollama\ollama.exe")
    if Path(windows_default).exists():
        return windows_default
    raise FileNotFoundError("Ollama executable not found on PATH.")


def register_model(ollama_exe: str, model_name: str, modelfile: Path) -> bool:
    """Creates (or updates) an Ollama model from a Modelfile."""
    print(f"[*] Registering '{model_name}' from {modelfile.name}...")
    cmd = [ollama_exe, "create", model_name, "-f", str(modelfile)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[OK] Model '{model_name}' registered.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to register '{model_name}': {e.stderr}")
        return False


def register_all_models() -> bool:
    ollama_exe = find_ollama_executable()
    results = [register_model(ollama_exe, name, path) for name, path in MODELS]
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if register_all_models() else 1)
