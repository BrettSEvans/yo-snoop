"""Usage: uv run python -m spikes.p5_chat_post spaces/AAA spaces/BBB users/123"""
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from spikes.common import SECRETS_DIR, pdt_now

def post(chat, space: str, text: str):
    try:
        r = chat.spaces().messages().create(parent=space, body={"text": text}).execute()
        return "OK", r.get("name")
    except HttpError as e:
        return f"HTTP {e.resp.status}", str(e)[:200]

def main():
    good, decoy, user = sys.argv[1], sys.argv[2], sys.argv[3]
    creds = service_account.Credentials.from_service_account_file(
        str(SECRETS_DIR / "chat-key.json"), scopes=["https://www.googleapis.com/auth/chat.bot"])
    chat = build("chat", "v1", credentials=creds)
    print(pdt_now(), "positive", post(chat, good, f"<{user}> P5 probe: Snoop can post here."))
    print(pdt_now(), "negative", post(chat, decoy, "P5 probe: this must NOT post."))

if __name__ == "__main__":
    main()
