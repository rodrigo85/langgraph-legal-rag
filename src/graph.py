"""
Ponto de entrada legado mantido para retrocompatibilidade.
Redireciona para src.agent.graph.
"""
from src.agent.graph import build_graph

__all__ = ["build_graph"]

if __name__ == "__main__":
    app = build_graph()
    print("[OK] Grafo compilado via src.agent.graph com sucesso!")
