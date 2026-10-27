"""Serveur MCP "marches" : cours, rendements et comparaison d'actifs via Yahoo Finance."""

import logging
import math
import warnings

import pandas as pd
import yfinance as yf
from mcp.server.mcpserver import MCPServer

# yfinance est bavard (warnings pandas, 404 sur tickers inconnus) : on gère les erreurs nous-mêmes.
warnings.filterwarnings("ignore", module="yfinance")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

mcp = MCPServer(
    "marches",
    instructions=(
        "Données de marché Yahoo Finance. Tickers au format Yahoo : AAPL, MSFT, "
        "IWDA.AS (Euronext Amsterdam), MC.PA (Paris), ^GSPC (indices)..."
    ),
)

PERIODES = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]


class ErreurDonnees(Exception):
    pass


def _r(x: float) -> float | None:
    """Arrondit à 4 décimales (None si NaN)."""
    x = float(x)
    return None if math.isnan(x) else round(x, 4)


def _clotures(ticker: str, periode: str) -> pd.Series:
    """Série des cours de clôture ajustés, ou ErreurDonnees si vide/inconnu."""
    if periode not in PERIODES:
        raise ErreurDonnees(f"Période '{periode}' invalide. Valeurs possibles : {', '.join(PERIODES)}.")
    try:
        hist = yf.Ticker(ticker).history(period=periode, auto_adjust=True)
    except Exception as e:
        raise ErreurDonnees(f"Impossible de récupérer '{ticker}' : {e}") from e
    if hist is None or hist.empty or "Close" not in hist:
        raise ErreurDonnees(f"Aucune donnée pour '{ticker}' sur '{periode}' (ticker inconnu ou délisté ?).")
    clotures = hist["Close"].dropna()
    if clotures.empty:
        raise ErreurDonnees(f"Aucun cours de clôture pour '{ticker}' sur '{periode}'.")
    clotures.index = clotures.index.tz_localize(None).normalize()
    return clotures


def _devise(ticker: str) -> str:
    try:
        return yf.Ticker(ticker).fast_info["currency"] or "inconnue"
    except Exception:
        return "inconnue"


def _metriques(clotures: pd.Series) -> dict:
    rdt = clotures.pct_change().dropna()
    drawdown = clotures / clotures.cummax() - 1
    return {
        "rendement_total": _r(clotures.iloc[-1] / clotures.iloc[0] - 1),
        "volatilite_annualisee": _r(rdt.std() * math.sqrt(252)) if len(rdt) > 1 else None,
        "drawdown_max": _r(drawdown.min()),
        "nb_jours": len(clotures),
    }


@mcp.tool()
def prix(ticker: str, periode: str = "1y") -> dict:
    """Donne les cours d'une action, d'un ETF ou d'un indice sur une période :
    premier et dernier cours de clôture (avec leurs dates), plus haut, plus bas et devise.
    À utiliser pour "combien vaut X ?", "quel était le prix de X il y a un an ?",
    "entre quels niveaux X a-t-il évolué ?".

    Args:
        ticker: symbole Yahoo Finance (ex. AAPL, MSFT, IWDA.AS, MC.PA, ^GSPC).
        periode: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd ou max (défaut 1y).

    Les cours sont ajustés des dividendes et splits. Renvoie {"erreur": ...} si le ticker est inconnu.
    """
    try:
        c = _clotures(ticker, periode)
    except ErreurDonnees as e:
        return {"erreur": str(e)}
    return {
        "ticker": ticker,
        "periode": periode,
        "devise": _devise(ticker),
        "premier_cours": _r(c.iloc[0]),
        "date_premier": c.index[0].strftime("%Y-%m-%d"),
        "dernier_cours": _r(c.iloc[-1]),
        "date_dernier": c.index[-1].strftime("%Y-%m-%d"),
        "plus_haut": _r(c.max()),
        "plus_bas": _r(c.min()),
    }


@mcp.tool()
def rendements(ticker: str, periode: str = "1y") -> dict:
    """Calcule la performance et le risque d'un actif sur une période :
    rendement total, volatilité annualisée (écart-type des rendements journaliers × √252)
    et drawdown maximum (pire baisse depuis un sommet). Valeurs en décimales (0.12 = 12 %).
    À utiliser pour "combien a rapporté X ?", "X est-il risqué ?", "quelle a été la pire chute de X ?".

    Args:
        ticker: symbole Yahoo Finance (ex. AAPL, MSFT, IWDA.AS, MC.PA, ^GSPC).
        periode: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd ou max (défaut 1y).

    Renvoie {"erreur": ...} si le ticker est inconnu.
    """
    try:
        c = _clotures(ticker, periode)
    except ErreurDonnees as e:
        return {"erreur": str(e)}
    return {"ticker": ticker, "periode": periode, **_metriques(c)}


@mcp.tool()
def comparer(tickers: list[str], periode: str = "1y") -> dict:
    """Compare plusieurs actifs sur une même période : pour chacun, rendement total,
    volatilité annualisée et drawdown maximum, plus la matrice de corrélation
    des rendements journaliers (calculée sur les dates communes).
    À utiliser pour "AAPL ou MSFT ?", "mon portefeuille est-il diversifié ?",
    "ces actifs bougent-ils ensemble ?".

    Args:
        tickers: liste de symboles Yahoo Finance (ex. ["AAPL", "MSFT", "IWDA.AS"]).
        periode: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd ou max (défaut 1y).

    Un ticker invalide apparaît avec une erreur sans bloquer les autres.
    """
    tickers = list(dict.fromkeys(t.strip() for t in tickers if t and t.strip()))
    if not tickers:
        return {"erreur": "Aucun ticker fourni."}

    metriques, series = {}, {}
    for t in tickers:
        try:
            c = _clotures(t, periode)
        except ErreurDonnees as e:
            metriques[t] = {"erreur": str(e)}
            continue
        metriques[t] = _metriques(c)
        series[t] = c

    resultat = {"periode": periode, "metriques": metriques}
    if len(series) < 2:
        resultat["correlation"] = None
        resultat["note"] = "Il faut au moins 2 tickers valides pour une corrélation."
        return resultat

    # Rendements calculés par série AVANT d'aligner (sinon un jour férié sur une place
    # crée des rendements sur 2 jours), puis corrélation paire par paire sur les dates communes.
    rdt = pd.DataFrame({t: c.pct_change() for t, c in series.items()}).iloc[1:]
    corr = rdt.corr()
    present = rdt.notna().astype(int)
    communs = present.T @ present
    resultat["correlation"] = {a: {b: _r(corr.loc[a, b]) for b in corr.columns} for a in corr.index}
    resultat["nb_jours_communs"] = {
        f"{a}/{b}": int(communs.loc[a, b]) for i, a in enumerate(communs.index) for b in communs.columns[i + 1 :]
    }
    return resultat


if __name__ == "__main__":
    mcp.run()
