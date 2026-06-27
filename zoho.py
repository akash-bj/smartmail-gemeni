import os
import html
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ACCOUNT_ID = os.getenv("ZOHO_ACCOUNT_ID")
FOLDER_ID = os.getenv("ZOHO_INBOX_FOLDER_ID")
ACCOUNTS_URL = os.getenv("ZOHO_ACCOUNTS_URL")
API_DOMAIN = os.getenv("ZOHO_API_DOMAIN")

ACCESS_TOKEN = None
ACCESS_TOKEN_EXPIRES_AT = 0


def get_access_token(force_refresh=False):
    global ACCESS_TOKEN, ACCESS_TOKEN_EXPIRES_AT

    if ACCESS_TOKEN and not force_refresh and ACCESS_TOKEN_EXPIRES_AT > 0:
        return ACCESS_TOKEN

    response = requests.post(
        f"{ACCOUNTS_URL}/oauth/v2/token",
        params={
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token"
        }
    )
    data = response.json()

    if "access_token" not in data:
        error_message = data.get("error_description") or data.get("error") or response.text
        raise RuntimeError(f"Zoho token error: {error_message}")

    ACCESS_TOKEN = data["access_token"]
    expires_in = int(data.get("expires_in", 3600))
    ACCESS_TOKEN_EXPIRES_AT = time.time() + expires_in - 60
    return ACCESS_TOKEN


def get_emails(limit=10, access_token=None):
    if access_token is None:
        access_token = get_access_token()

    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    url = f"{API_DOMAIN}/api/accounts/{ACCOUNT_ID}/messages/view"

    response = requests.get(
        url,
        headers=headers,
        params={"limit": limit, "sortorder": "false"}
    )
    return response.json()


def get_email_content(folder_id, message_id, access_token=None):
    if access_token is None:
        access_token = get_access_token()

    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    url = f"{API_DOMAIN}/api/accounts/{ACCOUNT_ID}/folders/{folder_id}/messages/{message_id}/content"

    response = requests.get(url, headers=headers)
    return response.json()["data"]["content"]


def clean_email_content(content):
    text = re.sub(r"<br\s*/?>", "\n", content, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()