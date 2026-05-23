"""
X Auto-Post Webhook API
Deploy len Render.com - nhan request tu Make.com va dang tweet len X.
"""

from flask import Flask, request, jsonify
import tweepy
import os

app = Flask(__name__)

def get_x_client():
    return tweepy.Client(
        consumer_key=os.environ["CONSUMER_KEY"],
        consumer_secret=os.environ["CONSUMER_SECRET"],
        access_token=os.environ["ACCESS_TOKEN"],
        access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
    )

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

    try:
        client = get_x_client()
        resp = client.create_tweet(text=text)
        tweet_id = str(resp.data["id"])
        return jsonify({"success": True, "tweet_id": tweet_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/thread", methods=["POST"])
def post_thread():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    tweets = data.get("tweets", [])

    if not tweets or not isinstance(tweets, list):
        return jsonify({"error": "Missing or invalid tweets list"}), 400

    try:
        client = get_x_client()
        prev_id = None
        ids = []
        for text in tweets:
            text = str(text).strip()
            if not text:
                continue
            if len(text) > 280:
                text = text[:277] + "..."
            kwargs = {"text": text}
            if prev_id:
                kwargs["in_reply_to_tweet_id"] = prev_id
            resp = client.create_tweet(**kwargs)
            prev_id = str(resp.data["id"])
            ids.append(prev_id)
        return jsonify({"success": True, "tweet_ids": ids}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
