"""Poll Meet REST participants for a live meeting; print each change with PDT time.
Usage: uv run python -m spikes.p1_meet_participants --code abc-defg-hij --as brett"""
import argparse, time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from spikes.common import SECRETS_DIR, pdt_now

SCOPES = ["https://www.googleapis.com/auth/meetings.space.readonly",
          "https://www.googleapis.com/auth/directory.readonly"]

def classify(p: dict) -> tuple[str, str | None, str]:
    if "signedinUser" in p:
        u = p["signedinUser"]
        return "signed_in", u.get("user"), u.get("displayName", "")
    if "phoneUser" in p:
        return "phone", None, p["phoneUser"].get("displayName", "")
    a = p.get("anonymousUser", {})
    return "anonymous", None, a.get("displayName", "")

def creds_for(who: str) -> Credentials:
    tok = SECRETS_DIR / f"token-{who}.json"
    if tok.exists():
        c = Credentials.from_authorized_user_file(str(tok), SCOPES)
        if c.valid:
            return c
        if c.expired and c.refresh_token:
            c.refresh(Request())
            tok.write_text(c.to_json()); tok.chmod(0o600)
            return c
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS_DIR / "client_secret.json"), SCOPES)
    c = flow.run_local_server(port=0)
    tok.write_text(c.to_json()); tok.chmod(0o600)
    return c

def email_for(people, user_id: str) -> str | None:
    pid = user_id.split("/", 1)[1]
    try:
        r = people.people().get(resourceName=f"people/{pid}", personFields="emailAddresses").execute()
        emails = r.get("emailAddresses", [])
        return emails[0]["value"] if emails else None
    except Exception as e:  # recorded, not hidden
        return f"LOOKUP-ERROR {type(e).__name__}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True)
    ap.add_argument("--as", dest="who", required=True)
    ap.add_argument("--seconds", type=int, default=300)
    a = ap.parse_args()
    c = creds_for(a.who)
    meet = build("meet", "v2", credentials=c)
    people = build("people", "v1", credentials=c)
    seen: dict[str, str] = {}
    end = time.monotonic() + a.seconds
    while time.monotonic() < end:
        t0 = time.monotonic()
        try:
            recs = meet.conferenceRecords().list(
                filter=f'space.meeting_code = "{a.code}" AND end_time IS NULL').execute()
        except Exception as e:
            print(pdt_now(), "LIST-ERROR", type(e).__name__, str(e)[:200]); time.sleep(1); continue
        for rec in recs.get("conferenceRecords", []):
            ps = meet.conferenceRecords().participants().list(parent=rec["name"]).execute()
            for p in ps.get("participants", []):
                kind, uid, name = classify(p)
                state = "left" if p.get("latestEndTime") else "present"
                key = p["name"]
                if seen.get(key) != state:
                    seen[key] = state
                    email = email_for(people, uid) if uid else None
                    print(pdt_now(), f"{state:7} {kind:9} {name!r} {email} api_ms={int((time.monotonic()-t0)*1000)}")
        time.sleep(max(0, 1 - (time.monotonic() - t0)))

if __name__ == "__main__":
    main()
