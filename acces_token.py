import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

TOKEN_URL = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token"


def get_access_token() -> str:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("CLIENT_ID ou CLIENT_SECRET manquant dans le fichier .env")

    # construction du scope comme indiqué dans la doc
    scope = f"api_offresdemploiv2 o2dsoffre application_{CLIENT_ID}"

    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": scope,
    }

    # realm=/partenaire doit être passé en query string
    params = {"realm": "/partenaire"}

    response = requests.post(TOKEN_URL, data=data, params=params)
    print("Status code:", response.status_code)
    print("Réponse brute:", response.text)  # pour debug

    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("Pas de access_token dans la réponse : " + response.text)

    return token


def main():
    token = get_access_token()
    print("\n✅ TOKEN RÉCUPÉRÉ :")
    print(token)


if __name__ == "__main__":
    main()