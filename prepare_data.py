import json
import pandas as pd


INPUT_FILE = "offres_data.json"
OUTPUT_FILE = "offres_data.csv"


def flatten_offer(offer: dict) -> dict:
    """
    Transforme un dictionnaire 'offre' (JSON brut de l'API)
    en une ligne simple pour le DataFrame.
    """

    # sous-blocs avec .get pour éviter les KeyError
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

        # Lieu
        "lieu_libelle": lieu.get("libelle"),
        "code_postal": lieu.get("codePostal"),
        "commune": lieu.get("commune"),
        "latitude": lieu.get("latitude"),
        "longitude": lieu.get("longitude"),

        # Salaire (peut être vide comme dans ton exemple)
        "salaire_libelle": salaire.get("libelle"),
        "salaire_min": salaire.get("salaireMin"),
        "salaire_max": salaire.get("salaireMax"),
        "salaire_unite": salaire.get("salaireUnite"),  # ex : A = annuel, M = mensuel, etc.

        # Autres infos utiles
        "duree_travail": offer.get("dureeTravailLibelle"),
        "alternance": offer.get("alternance"),
        "nombre_postes": offer.get("nombrePostes"),

        "nom_entreprise": entreprise.get("nom"),
        "secteur_activite": offer.get("secteurActiviteLibelle"),

        "date_creation": offer.get("dateCreation"),
        "date_actualisation": offer.get("dateActualisation"),
    }


def main():
    # 1) Charger le JSON brut
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        offres = json.load(f)

    print(f"Nombre d'offres dans le fichier JSON : {len(offres)}")

    # 2) Aplatir chaque offre
    rows = [flatten_offer(o) for o in offres]

    # 3) Construire le DataFrame
    df = pd.DataFrame(rows)
    print("\nAperçu du DataFrame :")
    print(df.head())

    # 4) Sauvegarder en CSV pour la suite de l'analyse
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"\n✅ Fichier CSV créé : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()