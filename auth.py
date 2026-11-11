"""Verify the Supabase session token the browser sends with every request."""
import functools
import os

import jwt
from flask import g, jsonify, request
from jwt import PyJWKClient

_jwks_client = None


def _jwks():
    """Public keys for projects that use Supabase's newer asymmetric signing keys."""
    global _jwks_client
    if _jwks_client is None:
        url = os.environ["SUPABASE_URL"].rstrip("/") + "/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(url)
    return _jwks_client


def verify_token(token):
    """Return the token's claims, or raise jwt.InvalidTokenError."""
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":  # legacy shared-secret projects
        key = os.environ["SUPABASE_JWT_SECRET"]
    elif alg in ("ES256", "RS256"):  # projects with asymmetric signing keys
        key = _jwks().get_signing_key_from_jwt(token).key
    else:
        raise jwt.InvalidTokenError(f"Unsupported algorithm: {alg}")
    return jwt.decode(token, key, algorithms=[alg], audience="authenticated")


def require_auth(view):
    """Reject the request unless it carries a valid Supabase token."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Log in to continue."), 401
        token = header[len("Bearer "):]
        try:
            claims = verify_token(token)
        except Exception:  # bad signature, expired, malformed, JWKS unreachable
            return jsonify(error="Your session expired. Log in again."), 401
        g.token = token
        g.user_id = claims["sub"]
        return view(*args, **kwargs)

    return wrapper
