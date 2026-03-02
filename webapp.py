from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, Response, flash, redirect, render_template_string, request, send_file, url_for

# --- Charge .env (CLIENT_ID / CLIENT_SECRET) ---
load_dotenv()

# --- Constantes API France Travail ---
OFFRES_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
TOKEN_URL = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token"

# --- Fichiers de sortie (dans le dossier courant) ---
RAW_JSON = "offres_data.json"
FLAT_CSV = "offres_data.csv"
FINAL_CSV = "offres_data_final.csv"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")


# -----------------------------
# Auth / Token
# -----------------------------

def get_access_token() -> str:
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("CLIENT_ID ou CLIENT_SECRET manquant dans le fichier .env")

    scope = f"api_offresdemploiv2 o2dsoffre application_{client_id}"

    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
    }

    # realm=/partenaire doit être passé en query string
    params = {"realm": "/partenaire"}

    r = requests.post(TOKEN_URL, data=data, params=params, timeout=30)
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError("Pas de access_token dans la réponse")
    return token


# -----------------------------
# Collecte API
# -----------------------------

def fetch_all_offers(token: str, mot_cle: str, step: int = 150, sleep_s: float = 0.1) -> List[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    all_offers: List[Dict[str, Any]] = []
    start = 0

    while True:
        end = start + step - 1
        range_str = f"{start}-{end}"

        params = {
            "motsCles": mot_cle,
            "range": range_str,
        }

        r = requests.get(OFFRES_URL, headers=headers, params=params, timeout=30)

        # 200 OK ou 206 Partial Content
        if r.status_code not in (200, 206):
            raise RuntimeError(f"Erreur API {r.status_code}: {r.text[:400]}")

        data = r.json()
        offers = data.get("resultats", [])
        if not offers:
            break

        all_offers.extend(offers)

        # si dernière page
        if len(offers) < step:
            break

        start += step
        time.sleep(sleep_s)

    return all_offers


# -----------------------------
# Préparation / flatten
# -----------------------------

def flatten_offer(offer: dict) -> dict:
    lieu = offer.get("lieuTravail", {}) or {}
    entreprise = offer.get("entreprise", {}) or {}
    salaire = offer.get("salaire", {}) or {}

    return {
        "description": offer.get("description"),
        "id": offer.get("id"),
        "intitule": offer.get("intitule"),
        "rome_code": offer.get("romeCode"),
        "rome_libelle": offer.get("romeLibelle"),
        "appellation_libelle": offer.get("appellationlibelle"),
        "type_contrat": offer.get("typeContrat"),
        "nature_contrat": offer.get("natureContrat"),
        "experience_exigee": offer.get("experienceExige"),
        "experience_libelle": offer.get("experienceLibelle"),
        "lieu_libelle": lieu.get("libelle"),
        "code_postal": lieu.get("codePostal"),
        "commune": lieu.get("commune"),
        "latitude": lieu.get("latitude"),
        "longitude": lieu.get("longitude"),
        "salaire_libelle": salaire.get("libelle"),
        "salaire_min": salaire.get("salaireMin"),
        "salaire_max": salaire.get("salaireMax"),
        "salaire_unite": salaire.get("salaireUnite"),
        "duree_travail": offer.get("dureeTravailLibelle"),
        "alternance": offer.get("alternance"),
        "nombre_postes": offer.get("nombrePostes"),
        "nom_entreprise": entreprise.get("nom"),
        "secteur_activite": offer.get("secteurActiviteLibelle"),
        "date_creation": offer.get("dateCreation"),
        "date_actualisation": offer.get("dateActualisation"),
    }


# -----------------------------
# Extraction salaire
# -----------------------------

def extract_salary_from_text(text: Any) -> float | None:
    if pd.isna(text):
        return None

    s = str(text).lower().replace(" ", "")

    # 1) Fourchette 40k-50k / 40kà50k
    m = re.search(r"(\d{2,3})k[-àa](\d{2,3})k", s)
    if m:
        low = int(m.group(1)) * 1000
        high = int(m.group(2)) * 1000
        return (low + high) / 2

    # 2) Fourchette 3000€-3500€
    m = re.search(r"(\d{3,5})€[-àa](\d{3,5})€", s)
    if m:
        low = int(m.group(1))
        high = int(m.group(2))
        if high < 10000:  # probablement mensuel
            return ((low + high) / 2) * 12
        return (low + high) / 2

    # 3) Mensuel 3000€ /mois
    m = re.search(r"(\d{3,4})€(?:/mois|mensuel|mois)?", s)
    if m:
        v = int(m.group(1))
        if v < 10000:
            return v * 12
        return float(v)

    # 4) Format 38k
    m = re.search(r"(\d{2,3})k", s)
    if m:
        return float(int(m.group(1)) * 1000)

    # 5) Format 45000€
    m = re.search(r"(\d{4,6})€", s)
    if m:
        return float(int(m.group(1)))

    return None


# -----------------------------
# Descriptif
# -----------------------------

def normalize_paris(libelle: Any) -> str | None:
    if pd.isna(libelle):
        return None
    s = str(libelle)
    if "paris" in s.lower():
        return "75 - Paris"
    return s


def run_pipeline(keywords: List[str]) -> Dict[str, Any]:
    t0 = time.time()

    token = get_access_token()

    all_offers: List[Dict[str, Any]] = []
    per_keyword_counts: List[Tuple[str, int]] = []

    for kw in keywords:
        offers_kw = fetch_all_offers(token, mot_cle=kw)
        per_keyword_counts.append((kw, len(offers_kw)))
        all_offers.extend(offers_kw)

    # dédoublonnage par id
    unique_offers = {o.get("id"): o for o in all_offers if o.get("id")}
    offers = list(unique_offers.values())

    # sauvegarde JSON brut
    with open(RAW_JSON, "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)

    # flatten -> CSV
    df = pd.DataFrame([flatten_offer(o) for o in offers])
    df.to_csv(FLAT_CSV, index=False, encoding="utf-8")

    # extraction salaire
    df["salaire_extrait"] = df["description"].apply(extract_salary_from_text)

    df_sal = df[df["salaire_extrait"].notna()].copy()
    df_sal = df_sal[(df_sal["salaire_extrait"] >= 20000) & (df_sal["salaire_extrait"] <= 200000)]
    df_sal.to_csv(FINAL_CSV, index=False, encoding="utf-8")

    # stats
    stats_salary = None
    if len(df_sal) > 0:
        s = df_sal["salaire_extrait"]
        stats_salary = {
            "min": float(s.min()),
            "max": float(s.max()),
            "mean": float(round(s.mean(), 2)),
            "median": float(s.median()),
            "count": int(s.notna().sum()),
        }

    # top villes
    df["ville_norm"] = df["lieu_libelle"].apply(normalize_paris)
    top_villes = df["ville_norm"].value_counts().head(10)

    # contrats
    contrats = df["type_contrat"].value_counts().head(10)

    # expérience
    exp = df["experience_libelle"].value_counts().head(10)

    elapsed = time.time() - t0

    return {
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "keywords": keywords,
        "per_keyword_counts": per_keyword_counts,
        "total_brut": len(all_offers),
        "total_unique": len(offers),
        "flat_rows": int(len(df)),
        "salary_stats": stats_salary,
        "salary_rows": int(len(df_sal)),
        "top_villes": top_villes.to_dict(),
        "contrats": contrats.to_dict(),
        "experience": exp.to_dict(),
        "elapsed_s": round(elapsed, 2),
    }


# -----------------------------
# UI (HTML minimal)
# -----------------------------

TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>France Travail – Interface locale</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
    .wrap { max-width: 980px; margin: 0 auto; }
    .card { border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; margin: 16px 0; }
    input[type=text] { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 10px; }
    button { padding: 10px 14px; border-radius: 10px; border: 0; cursor: pointer; }
    .btn { background: #111827; color: white; }
    .muted { color: #6b7280; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eee; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 800px) { .row { grid-template-columns: 1fr; } }
    .flash { padding: 10px; border-radius: 10px; margin: 10px 0; }
    .flash.error { background: #fee2e2; color: #991b1b; }
    .flash.ok { background: #dcfce7; color: #166534; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>France Travail – Interface locale</h1>
  <p class="muted">Lance la collecte via l'API, prépare le CSV, extrait les salaires, et affiche quelques stats.</p>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class="flash {{category}}">{{message}}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <div class="card">
    <h2>1) Lancer la pipeline</h2>
    <form method="post" action="{{ url_for('run') }}">
      <label>Mots-clés (séparés par des virgules)</label>
      <input type="text" name="keywords" value="{{ default_keywords }}" />
      <p class="muted">Ex: data, analyst, scientist, machine learning, statisticien</p>
      <button class="btn" type="submit">▶ Exécuter</button>
    </form>
  </div>

  {% if result %}
  <div class="card">
    <h2>2) Résumé</h2>
    <p><b>Date</b> : {{ result.run_at }} — <b>Durée</b> : {{ result.elapsed_s }} s</p>
    <ul>
      <li><b>Offres brutes</b> : {{ result.total_brut }}</li>
      <li><b>Offres uniques (id)</b> : {{ result.total_unique }}</li>
      <li><b>Lignes CSV</b> : {{ result.flat_rows }}</li>
      <li><b>Lignes avec salaire exploitable</b> : {{ result.salary_rows }}</li>
    </ul>

    <h3>Détail par mot-clé</h3>
    <table>
      <thead><tr><th>Mot-clé</th><th>Offres récupérées</th></tr></thead>
      <tbody>
      {% for kw, n in result.per_keyword_counts %}
        <tr><td>{{ kw }}</td><td>{{ n }}</td></tr>
      {% endfor %}
      </tbody>
    </table>

    <h3>Fichiers générés</h3>
    <ul>
      <li><a href="{{ url_for('download', filename='offres_data.json') }}">Télécharger offres_data.json</a></li>
      <li><a href="{{ url_for('download', filename='offres_data.csv') }}">Télécharger offres_data.csv</a></li>
      <li><a href="{{ url_for('download', filename='offres_data_final.csv') }}">Télécharger offres_data_final.csv</a></li>
    </ul>
  </div>

  <div class="row">
    <div class="card">
      <h2>3) Salaires (annuels, €)</h2>
      {% if result.salary_stats %}
        <ul>
          <li><b>Min</b> : {{ result.salary_stats.min }}</li>
          <li><b>Max</b> : {{ result.salary_stats.max }}</li>
          <li><b>Moyenne</b> : {{ result.salary_stats.mean }}</li>
          <li><b>Médiane</b> : {{ result.salary_stats.median }}</li>
          <li><b>N</b> : {{ result.salary_stats.count }}</li>
        </ul>
      {% else %}
        <p class="muted">Aucun salaire exploitable trouvé.</p>
      {% endif %}
    </div>

    <div class="card">
      <h2>4) Top villes</h2>
      <table>
        <thead><tr><th>Ville</th><th>Nb</th></tr></thead>
        <tbody>
        {% for k,v in result.top_villes.items() %}
          <tr><td>{{ k }}</td><td>{{ v }}</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <div class="row">
    <div class="card">
      <h2>5) Types de contrat (top)</h2>
      <table>
        <thead><tr><th>Type</th><th>Nb</th></tr></thead>
        <tbody>
        {% for k,v in result.contrats.items() %}
          <tr><td>{{ k }}</td><td>{{ v }}</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>6) Expérience (top)</h2>
      <table>
        <thead><tr><th>Libellé</th><th>Nb</th></tr></thead>
        <tbody>
        {% for k,v in result.experience.items() %}
          <tr><td>{{ k }}</td><td>{{ v }}</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  {% endif %}
</div>
</body>
</html>
"""


@app.get("/")
def index() -> str:
    default_keywords = "data, analyst, scientist, machine learning, statisticien, économètre, bi"
    return render_template_string(TEMPLATE, result=None, default_keywords=default_keywords)


@app.post("/run")
def run() -> Response:
    raw = (request.form.get("keywords") or "").strip()
    if not raw:
        flash("error\nAucun mot-clé fourni.", "error")
        return redirect(url_for("index"))

    keywords = [k.strip() for k in raw.split(",") if k.strip()]

    try:
        result = run_pipeline(keywords)
        flash("Pipeline terminée ✅", "ok")
        default_keywords = raw
        return render_template_string(TEMPLATE, result=result, default_keywords=default_keywords)
    except Exception as e:
        flash(f"Erreur: {type(e).__name__}: {e}", "error")
        return redirect(url_for("index"))


@app.get("/download/<path:filename>")
def download(filename: str):
    # sécurité minimale: autoriser seulement nos 3 fichiers
    allowed = {RAW_JSON, FLAT_CSV, FINAL_CSV}
    if filename not in allowed:
        return ("Fichier non autorisé", 403)
    if not os.path.exists(filename):
        return ("Fichier introuvable", 404)
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    # host=127.0.0.1 (local), port=5000
    app.run(host="127.0.0.1", port=5000, debug=True)
