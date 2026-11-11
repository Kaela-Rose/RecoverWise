"""Every database read and write the app needs, in one place."""
import db
from db import SupabaseError

PLAN_TREE = (
    "id,slug,name,description,"
    "phases(id,phase_number,name,summary,min_days,"
    "steps(id,position,kind,title,instructions,youtube_id))"
)


def list_plans(token):
    resp = db.rest(
        "GET",
        "plans",
        token,
        params={
            "select": "id,slug,name,description,phases(phase_number,name,min_days)",
            "order": "name.asc",
        },
    )
    plans = resp.json()
    for plan in plans:
        plan["phases"].sort(key=lambda p: p["phase_number"])
    return plans


def get_plan(token, plan_id):
    """One plan with all its phases and steps, or None."""
    resp = db.rest(
        "GET", "plans", token, params={"select": PLAN_TREE, "id": f"eq.{plan_id}"}
    )
    rows = resp.json()
    return rows[0] if rows else None


def get_user_plan(token, user_id):
    resp = db.rest(
        "GET", "user_plans", token, params={"select": "*", "user_id": f"eq.{user_id}"}
    )
    rows = resp.json()
    return rows[0] if rows else None


def save_user_plan(token, user_id, plan_id, started_on):
    """Pick (or switch) a plan: start Phase 1 today."""
    db.rest(
        "POST",
        "user_plans",
        token,
        params={"on_conflict": "user_id"},
        body={
            "user_id": user_id,
            "plan_id": plan_id,
            "phase_number": 1,
            "phase_started_on": started_on,
            "finished": False,
        },
        headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
    )


def update_user_plan(token, user_id, **fields):
    db.rest(
        "PATCH",
        "user_plans",
        token,
        params={"user_id": f"eq.{user_id}"},
        body=fields,
        headers={"Prefer": "return=minimal"},
    )


def completions_since(token, user_id, step_ids, since):
    """Completion rows for these steps on or after the given date."""
    if not step_ids:
        return []
    resp = db.rest(
        "GET",
        "completions",
        token,
        params={
            "select": "step_id,completed_on",
            "user_id": f"eq.{user_id}",
            "step_id": "in.(" + ",".join(str(i) for i in step_ids) + ")",
            "completed_on": f"gte.{since}",
        },
    )
    return resp.json()


def add_completion(token, user_id, step_id, day):
    try:
        db.rest(
            "POST",
            "completions",
            token,
            body={"user_id": user_id, "step_id": step_id, "completed_on": day},
            headers={"Prefer": "return=minimal"},
        )
    except SupabaseError as exc:
        if exc.status != 409:  # 409 = already checked off today, which is fine
            raise


def count_completions(token, user_id):
    resp = db.rest(
        "GET",
        "completions",
        token,
        params={"select": "id", "user_id": f"eq.{user_id}"},
        headers={"Prefer": "count=exact", "Range": "0-0"},
    )
    return int(resp.headers.get("Content-Range", "*/0").split("/")[-1])


def delete_account(token):
    """Calls the delete_my_account() SQL function (see db/schema.sql)."""
    db.rest("POST", "rpc/delete_my_account", token, body={})
