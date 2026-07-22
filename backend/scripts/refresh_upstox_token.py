"""
Automates the annoying half of Upstox's daily token cycle.

WHAT UPSTOX STILL REQUIRES OF YOU (can't be automated away): logging in
through Upstox's hosted login page (username/password + TOTP) once per
trading day and grabbing the `code` param Upstox redirects you back with.
Upstox does not offer a long-lived refresh token -- this manual login is
how their API is designed, not a gap in this script.

WHAT THIS SCRIPT AUTOMATES: everything after you have that code.
  1. Exchanges the authorization `code` for an access token
     (POST /v2/login/authorization/token).
  2. If RENDER_API_KEY + RENDER_SERVICE_ID are set, pushes the new token
     straight into your Render service's env vars and triggers a redeploy
     via the Render API -- so you don't have to open the Render dashboard
     and paste it in by hand.
  3. Otherwise, just prints the token so you can paste it into
     UPSTOX_ACCESS_TOKEN on Render yourself.

DAILY WORKFLOW:
  1. Open (in a browser, once per trading day):
       https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=<UPSTOX_API_KEY>&redirect_uri=<UPSTOX_REDIRECT_URI>
     Log in, approve, and copy the `code=...` value from the redirect URL.
  2. Run:
       python scripts/refresh_upstox_token.py --code <code>

REQUIRES (env vars, e.g. in backend/.env loaded via python-dotenv, or just
exported in your shell):
  UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REDIRECT_URI  (from your
    Upstox developer app at https://upstox.com/developer/apps)
  RENDER_API_KEY, RENDER_SERVICE_ID  (optional -- enables step 2; get an
    API key from Render's account settings, and the service ID from your
    service's URL / Render API "list services" call)
"""
import argparse
import os
import sys

import requests

UPSTOX_TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"
RENDER_API_BASE = "https://api.render.com/v1"


def exchange_code_for_token(code: str) -> str:
    api_key = os.environ["UPSTOX_API_KEY"]
    api_secret = os.environ["UPSTOX_API_SECRET"]
    redirect_uri = os.environ["UPSTOX_REDIRECT_URI"]

    resp = requests.post(
        UPSTOX_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        data={
            "code": code,
            "client_id": api_key,
            "client_secret": api_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Upstox token exchange failed ({resp.status_code}): {resp.text[:500]}")
    body = resp.json()
    token = body.get("access_token")
    if not token:
        raise RuntimeError(f"Upstox response had no access_token: {body}")
    return token


def push_token_to_render(token: str) -> bool:
    """Updates UPSTOX_ACCESS_TOKEN on the Render service and lets Render's
    own env-var-change auto-deploy handle the restart. Returns True if the
    Render API call succeeded, False if Render env vars aren't configured
    (caller should fall back to printing the token)."""
    render_key = os.getenv("RENDER_API_KEY")
    service_id = os.getenv("RENDER_SERVICE_ID")
    if not render_key or not service_id:
        return False

    headers = {"Authorization": f"Bearer {render_key}", "Accept": "application/json"}

    # Render's env-vars endpoint replaces the *entire* env var list, so we
    # must fetch the current set first and only change UPSTOX_ACCESS_TOKEN --
    # PUTting a single-var payload would silently wipe every other env var
    # (LIVE_NSE, SUPABASE_URL, etc.) on the service.
    get_resp = requests.get(f"{RENDER_API_BASE}/services/{service_id}/env-vars", headers=headers, timeout=15)
    get_resp.raise_for_status()
    current = {item["envVar"]["key"]: item["envVar"]["value"] for item in get_resp.json()}
    current["UPSTOX_ACCESS_TOKEN"] = token

    put_resp = requests.put(
        f"{RENDER_API_BASE}/services/{service_id}/env-vars",
        headers={**headers, "Content-Type": "application/json"},
        json=[{"key": k, "value": v} for k, v in current.items()],
        timeout=15,
    )
    put_resp.raise_for_status()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--code", required=True, help="The `code` param Upstox redirected you with today")
    args = parser.parse_args()

    try:
        token = exchange_code_for_token(args.code)
    except (KeyError, RuntimeError) as exc:
        print(f"Token exchange failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Access token obtained.")

    try:
        pushed = push_token_to_render(token)
    except requests.RequestException as exc:
        print(f"Render API call failed, falling back to manual paste: {exc}", file=sys.stderr)
        pushed = False

    if pushed:
        print("UPSTOX_ACCESS_TOKEN updated on Render -- redeploy should trigger automatically.")
    else:
        print("RENDER_API_KEY/RENDER_SERVICE_ID not set (or the push failed) -- "
              "paste this into UPSTOX_ACCESS_TOKEN on Render manually:")
        print(token)


if __name__ == "__main__":
    main()
