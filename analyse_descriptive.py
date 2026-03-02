import pandas as pd
import re

# Fichier avec TOUTES les offres (≈ 3000)
FULL_FILE = "offres_data.csv"

# Fichier avec seulement les offres ayant un salaire exploitable (≈ 233)
SALARY_FILE = "offres_data_final.csv"


def normalize_paris(libelle: str) -> str | None:
    """Regroupe toutes les variantes de Paris en '75 - Paris'."""
    if pd.isna(libelle):
        return None
    s = str(libelle)
    if "paris" in s.lower():
        return "75 - Paris"
    return s


def main():
    # ---------- Chargement des données ----------
    df_full = pd.read_csv(FULL_FILE)
    df_sal = pd.read_csv(SALARY_FILE)

    print("=== TAILLE DES JEUX DE DONNÉES ===")
    print("Offres totales (df_full) :", len(df_full))
    print("Offres avec salaire (df_sal) :", len(df_sal))

    # ---------- STATISTIQUES SALARIALES (sur df_sal) ----------
    print("\n===== STATISTIQUES SALARIALES (offres avec salaire) =====")
    print("Salaire min :", df_sal["salaire_extrait"].min())
    print("Salaire max :", df_sal["salaire_extrait"].max())
    print("Salaire moyen :", round(df_sal["salaire_extrait"].mean(), 2))
    print("Salaire médian :", df_sal["salaire_extrait"].median())

    # ---------- TOP VILLES (sur df_full, avec regroupement Paris) ----------
    print("\n===== TOP 10 VILLES (toutes offres) =====")
    df_full["ville_norm"] = df_full["lieu_libelle"].apply(normalize_paris)
    top_villes = df_full["ville_norm"].value_counts().head(10)
    print(top_villes)

    # ---------- TYPES DE CONTRAT (sur df_full) ----------
    print("\n===== TYPES DE CONTRAT (toutes offres) =====")
    print(df_full["type_contrat"].value_counts())

    # ---------- EXPERIENCE DEMANDÉE (sur df_full) ----------
    print("\n===== EXPERIENCE DEMANDÉE (toutes offres) =====")
    print(df_full["experience_libelle"].value_counts().head(10))

    # ---------- COMPÉTENCES FRÉQUENTES (sur df_full) ----------
    print("\n===== COMPETENCES LES PLUS CITEES (toutes offres) =====")

    competences = [
        "python",
        "sql",
        "power bi",
        "tableau",
        "excel",
        "aws",
        "azure",
        "machine learning",
        "r",
        "spark",
        "pandas",
        "tensorflow",
    ]

    # concaténation de toutes les descriptions des ~3000 offres
    text_all = " ".join(df_full["description"].astype(str)).lower()

    counts: dict[str, int] = {}
    for comp in competences:
        # \b : limite de mot → évite que "r" matche toutes les lettres "r"
        pattern = r"\b" + re.escape(comp) + r"\b"
        counts[comp] = len(re.findall(pattern, text_all))

    sorted_counts = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    for tech, n in sorted_counts.items():
        print(f"{tech} : {n}")


if __name__ == "__main__":
    main()