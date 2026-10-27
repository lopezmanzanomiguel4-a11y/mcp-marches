# marches — serveur MCP de données de marché

Serveur MCP (Python, stdio) qui donne à Claude des données Yahoo Finance via `yfinance`.

| Outil | Ce qu'il renvoie |
|---|---|
| `prix(ticker, periode="1y")` | premier et dernier cours, plus haut, plus bas, devise |
| `rendements(ticker, periode="1y")` | rendement total, volatilité annualisée (σ journalier × √252), drawdown max |
| `comparer(tickers, periode="1y")` | les métriques de `rendements` par ticker + la matrice de corrélation des rendements journaliers |

Périodes : `1d 5d 1mo 3mo 6mo 1y 2y 5y 10y ytd max`. Les cours sont ajustés des dividendes et des splits, et les résultats arrondis à 4 décimales. Un ticker inconnu renvoie `{"erreur": ...}` au lieu de planter.

## Installation (Windows, Python 3.10+)

```powershell
git clone https://github.com/lopezmanzanomiguel4-a11y/mcp-marches.git
cd mcp-marches
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe test_outils.py   # vérifie que tout répond
```

Brancher sur Claude Code (tous les projets), avec des chemins absolus :

```powershell
claude mcp add --scope user marches -- "$PWD\.venv\Scripts\python.exe" "$PWD\server.py"
claude mcp list
```

Ensuite, redémarre Claude Code.

## Exemples de questions

- « Combien vaut IWDA.AS aujourd'hui, et quel était son plus bas sur 1 an ? »
- « Quelle a été la volatilité de MSFT sur 5 ans ? Et son pire drawdown ? »
- « Compare AAPL, MSFT et IWDA.AS depuis le début de l'année. »
- « Est-ce qu'ajouter de l'or (GC=F) à un ETF monde diversifie vraiment ? Regarde les corrélations. »

Les tickers suivent le format Yahoo : suffixe `.AS` pour Amsterdam, `.PA` pour Paris, `.BR` pour Bruxelles, et `^` pour les indices (`^GSPC`).
