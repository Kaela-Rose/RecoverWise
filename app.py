"""RecoverWise backend (starter).

Routes so far:
  GET /         -> a short message so the home page isn't a 404
  GET /health   -> quick check that the server is running
  GET /plans    -> a hardcoded list of the three sample recovery plans

Later, /plans will read from the recovery_plans table in Supabase,
and every user route will verify the Supabase token first.
"""

from dotenv import load_dotenv
from flask import Flask, jsonify

# Reads values from a local .env file (kept out of GitHub by .gitignore).
load_dotenv()

app = Flask(__name__)

# Hardcoded for now. Replace with a Supabase query once the tables exist.
PLANS = [
    {
        "id": 1,
        "name": "ACL tear",
        "description": "Sample routine for recovering from an ACL tear: "
        "gentle knee movement first, then strength, stairs, and everyday tasks.",
    },
    {
        "id": 2,
        "name": "Herniated disc",
        "description": "Sample routine for a herniated disc: "
        "gentle core and back control first, then everyday tasks like "
        "getting out of bed and lifting safely.",
    },
    {
        "id": 3,
        "name": "Rotator cuff tear",
        "description": "Sample routine for a rotator cuff tear: "
        "gentle shoulder motion first, then strength and everyday tasks "
        "like reaching a shelf.",
    },
]


@app.get("/")
def home():
    return "RecoverWise API is running. Try /plans"


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/plans")
def get_plans():
    return jsonify(PLANS)


if __name__ == "__main__":
    app.run(debug=True)
