from flask import Flask, request, jsonify
import tweepy
import os

app = Flask(__name__)


def check_auth(req):
        return req.headers.get("X-Webhook-Secret") == os.environ.get("WEBHOOK_SECRET", "")


def get_client():
        """Twitter API v2 client (OAuth 1.0a User Context) - requires Read+Write app permissions."""
        return tweepy.Client(
            consumer_key=os.environ["CONSUMER_KEY"],
            consumer_secret=os.environ["CONSUMER_SECRET"],
            access_token=os.environ["ACCESS_TOKEN"],
            access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
        )


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
                client = get_client()
                response = client.create_tweet(text=text)
                tweet_id = str(response.data["id"])
                tweet_url = f"https://x.com/i/web/status/{tweet_id}"
                return jsonify({"success": True, "tweet_id": tweet_id, "url": tweet_url}), 200
except tweepy.errors.Forbidden as e:
            return jsonify({"error": f"Forbidden: {str(e)}"}), 403
except tweepy.errors.TweepyException as e:
            return jsonify({"error": f"Twitter error: {str(e)}"}), 500
except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
        return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    
