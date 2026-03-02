import requests
import time
import json

from acces_token import get_access_token

OFFRES_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"


def fetch_all_offers(token: str, mot_cle="data"):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    all_offers = []
    start = 0
    step = 150

    while True:
        end = start + step - 1
        range_str = f"{start}-{end}"

        params = {
            "motsCles": mot_cle,
            "range": range_str,
        }

        print(f"Requête pour range {range_str}")

        response = requests.get(OFFRES_URL, headers=headers, params=params)

        if response.status_code not in (200, 206):
            print("Erreur API :", response.status_code)
            break

        data = response.json()
        offers = data.get("resultats", [])

        if not offers:
            print("Plus d'offres trouvées.")
            break

        all_offers.extend(offers)

        print(f"Total cumulé : {len(all_offers)}")

        if len(offers) < step:
            break

        start += step
        time.sleep(0.1)

    return all_offers


def main():
    token = get_access_token()
    print("✅ Token récupéré")

    keywords = [
        "data",
        "analyst",
        "scientist",
        "machine learning",
        "statisticien",
        "économètre",
        "bi"
    ]

    all_offers = []

    for word in keywords:
        print(f"\nRecherche pour : {word}")
        offers = fetch_all_offers(token, mot_cle=word)
        all_offers.extend(offers)

    print("\nTotal brut cumulé :", len(all_offers))

    # Suppression des doublons via id
    unique_offers = {offer["id"]: offer for offer in all_offers}
    offers = list(unique_offers.values())

    print("Total après suppression doublons :", len(offers))

    # Sauvegarde JSON
    with open("offres_data.json", "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)

    print("✅ Fichier 'offres_data.json' créé avec succès")


if __name__ == "__main__":
    main()