# extract_salary.py

import pandas as pd
import re

INPUT_FILE = "offres_data.csv"
OUTPUT_FILE_FINAL = "offres_data_final.csv"


def extract_salary(text):
    if pd.isna(text):
        return None

    text = text.lower().replace(" ", "")

    # ---- 1️⃣ Fourchette type 40k-50k ----
    match_range_k = re.search(r"(\d{2,3})k[-àa](\d{2,3})k", text)
    if match_range_k:
        low = int(match_range_k.group(1)) * 1000
        high = int(match_range_k.group(2)) * 1000
        return (low + high) / 2

    # ---- 2️⃣ Fourchette type 3000€-3500€ ----
    match_range_euro = re.search(r"(\d{3,5})€[-àa](\d{3,5})€", text)
    if match_range_euro:
        low = int(match_range_euro.group(1))
        high = int(match_range_euro.group(2))
        # suppose mensuel si petit nombre
        if high < 10000:
            return ((low + high) / 2) * 12
        return (low + high) / 2

    # ---- 3️⃣ Mensuel type 3000€ ----
    match_month = re.search(r"(\d{3,4})€(?:/mois|mensuel|mois)?", text)
    if match_month:
        value = int(match_month.group(1))
        if value < 10000:  # probablement mensuel
            return value * 12
        return value

    # ---- 4️⃣ Format 38k ----
    match_k = re.search(r"(\d{2,3})k", text)
    if match_k:
        return int(match_k.group(1)) * 1000

    # ---- 5️⃣ Format 45000€ ----
    match_euro = re.search(r"(\d{4,6})€", text)
    if match_euro:
        return int(match_euro.group(1))

    return None


def main():
    df = pd.read_csv(INPUT_FILE)

    print("Nombre total d'offres :", len(df))

    df["salaire_extrait"] = df["description"].apply(extract_salary)

    print("Nombre d'offres avec salaire extrait :",
          df["salaire_extrait"].notna().sum())

    # Nettoyage réaliste
    df_clean = df[
        (df["salaire_extrait"] >= 20000) &
        (df["salaire_extrait"] <= 200000)
    ]

    print("\nNombre après nettoyage :", len(df_clean))
    print("\nStatistiques après nettoyage :")
    print(df_clean["salaire_extrait"].describe())

    df_clean.to_csv(OUTPUT_FILE_FINAL, index=False)
    print("\n✅ Fichier final créé :", OUTPUT_FILE_FINAL)


if __name__ == "__main__":
    main()