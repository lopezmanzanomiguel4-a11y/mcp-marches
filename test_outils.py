"""Appelle les 3 outils directement (sans passer par MCP) pour vérifier qu'ils marchent."""

import json

from server import comparer, prix, rendements

TICKERS = ["AAPL", "MSFT", "IWDA.AS"]


def afficher(titre, resultat):
    print(f"\n=== {titre} ===")
    print(json.dumps(resultat, indent=2, ensure_ascii=False))


for t in TICKERS:
    afficher(f"prix({t})", prix(t))
    afficher(f"rendements({t})", rendements(t))

afficher("comparer(AAPL, MSFT, IWDA.AS)", comparer(TICKERS))

# Robustesse : ticker bidon et période invalide
afficher("prix(XXXXINVALIDE)", prix("XXXXINVALIDE"))
afficher("rendements(AAPL, periode='3ans')", rendements("AAPL", "3ans"))
afficher("comparer(AAPL, XXXXINVALIDE)", comparer(["AAPL", "XXXXINVALIDE"]))
