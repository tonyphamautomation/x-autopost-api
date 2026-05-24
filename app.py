from flask import Flask, request, jsonify
import os
import requests as http_requests
import time

app = Flask(__name__)

# In-memory token cache
_token_cache = {"access_token": None, "expires_at": 0}


def refresh_access_token():
    """Use refresh token to get a new OAuth 2.0 access token."""
    refresh_token = os.environ.get("OAUTH2_REFRESH_TOKEN", "")
    client_id = os.environ.get("CLIENT_ID", "")
    client_secret = os.environ.get("CLIENT_SECRET", "")

    if not refresh_token or not client_id:
        return None

    try:
        auth = (client_id, client_secret) if client_secret else None
        resp = http_requests.post(
            "https://api.twitter.com/2/oauth2/token",
            auth=auth,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        if resp.ok:
            data = resp.json()
            _token_cache["access_token"] = data["access_token"]
            _token_cache["expires_at"] = time.time() + data.get("expires_in", 7200)
            if "refresh_token" in data:
                os.environ["OAUTH2_REFRESH_TOKEN"] = data["refresh_token"]
            return _token_cache["access_token"]
        else:
            app.logger.error(f"Token refresh failed: {resp.status_code} {resp.text}")
    except Exception as e:
        app.logger.error(f"Token refresh exception: {e}")
    return None


def get_access_token():
    """Get a valid OAuth 2.0 access token, refreshing if needed."""
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 300:
        return _token_cache["access_token"]
    return refresh_access_token()


def check_auth(req):
    return req.headers.get("X-Webhook-Secret") == os.environ.get("WEBHOOK_SECRET", "")


@app.route("/tweet", methods=["POST"])
def post_tweet():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "Missing text field"}), 400

    if len(text) > 280:
        text = text[:277] + "..."

    token = get_access_token()
    if not token:
        return jsonify({"error": "Could not obtain OAuth 2.0 access token"}), 500

    try:
        resp = http_requests.post(
            "https://api.twitter.com/2/tweets",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"text": text},
            timeout=30,
        )
        if resp.status_code == 201:
            tweet_data = resp.json().get("data", {})
            tweet_id = str(tweet_data.get("id", ""))
            tweet_url = f"https://x.com/i/web/status/{tweet_id}"
            return jsonify({"success": True, "tweet_id": tweet_id, "url": tweet_url}), 200
        else:
            return jsonify({"error": f"Twitter API {resp.status_code}: {resp.text}"}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
