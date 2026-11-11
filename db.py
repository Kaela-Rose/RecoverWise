"""Tiny PostgREST client.

Every call is made with the *user's* token, so Postgres row-level security
decides what that user can read and write. Flask never holds a service key.
"""
import os

import requests


class SupabaseError(Exception):
    def __init__(self, status, detail):
        super().__init__(f"Supabase returned {status}: {detail}")
        self.status = status
        self.detail = detail


def rest(method, path, token, params=None, body=None, headers=None):
    """Call /rest/v1/<path> as the signed-in user and return the response."""
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path
    all_headers = {
        "apikey": os.environ["SUPABASE_ANON_KEY"],
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    all_headers.update(headers or {})
    resp = requests.request(
        method, url, headers=all_headers, params=params, json=body, timeout=10
    )
    if resp.status_code >= 400:
        raise SupabaseError(resp.status_code, resp.text)
    return resp
