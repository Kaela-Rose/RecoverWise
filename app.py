"""RecoverWise Flask API: serves the frontend and enforces the game rules."""
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request, send_from_directory

load_dotenv()

import progress  # noqa: E402
import repo  # noqa: E402
from auth import require_auth  # noqa: E402
from db import SupabaseError  # noqa: E402

app = Flask(__name__, static_folder="static", static_url_path="/static")
log = logging.getLogger(__name__)


def error(message, status, **extra):
    return jsonify({"error": message, **extra}), status


@app.errorhandler(SupabaseError)
def handle_supabase_error(exc):
    log.warning("Supabase error %s: %s", exc.status, exc.detail)
    if exc.status == 401:
        return error("Your session expired. Log in again.", 401)
    if exc.status == 403:
        return error("You are not allowed to do that.", 403)
    return error("The database had a problem. Try again in a moment.", 502)


def client_today():
    """Today's date in the user's time zone (sent by the browser), else UTC."""
    try:
        zone = ZoneInfo(request.headers.get("X-Timezone") or "UTC")
    except Exception:
        zone = ZoneInfo("UTC")
    return datetime.now(zone).date()


def load_context():
    """The user's plan, phases and current steps, or None if no plan chosen."""
    user_plan = repo.get_user_plan(g.token, g.user_id)
    if user_plan is None:
        return None
    plan = repo.get_plan(g.token, user_plan["plan_id"])
    phases = sorted(plan["phases"], key=lambda p: p["phase_number"])
    phase = next(
        (p for p in phases if p["phase_number"] == user_plan["phase_number"]), None
    )
    if phase is None:
        raise RuntimeError("User is on a phase that does not exist")
    steps = sorted(phase["steps"], key=lambda s: s["position"])
    return {
        "user_plan": user_plan,
        "plan": plan,
        "phases": phases,
        "phase": phase,
        "steps": steps,
    }


def build_progress(ctx, today):
    """Plan, phase, XP and day counts for the current phase."""
    steps, phase, user_plan = ctx["steps"], ctx["phase"], ctx["user_plan"]
    rows = repo.completions_since(
        g.token, g.user_id, [s["id"] for s in steps], user_plan["phase_started_on"]
    )
    summary = progress.summarize(steps, rows, today.isoformat())
    total_phases = len(ctx["phases"])
    is_last = phase["phase_number"] == total_phases
    finished = user_plan["finished"]
    payload = {
        "plan": {
            "id": ctx["plan"]["id"],
            "slug": ctx["plan"]["slug"],
            "name": ctx["plan"]["name"],
        },
        "phase": {
            "number": phase["phase_number"],
            "name": phase["name"],
            "summary": phase["summary"],
            "min_days": phase["min_days"],
            "total_phases": total_phases,
        },
        "days_completed": summary["full_days"],
        "can_advance": (not finished) and summary["full_days"] >= phase["min_days"],
        "is_last_phase": is_last,
        "finished": finished,
        "xp": {
            "total": repo.count_completions(g.token, g.user_id) * progress.XP_PER_STEP,
            "phase": summary["phase_completions"] * progress.XP_PER_STEP,
            "phase_goal": len(steps) * phase["min_days"] * progress.XP_PER_STEP,
            "today": len(summary["done_today"]) * progress.XP_PER_STEP,
            "today_max": len(steps) * progress.XP_PER_STEP,
        },
    }
    return payload, summary


def today_payload(ctx, today):
    prog, summary = build_progress(ctx, today)
    return {
        "date": today.isoformat(),
        "steps": progress.flag_steps(ctx["steps"], summary["done_today"]),
        "day_complete": summary["day_complete"],
        "progress": prog,
    }


# --- Pages and public routes -------------------------------------------------


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/config")
def public_config():
    """Public values the browser needs to talk to Supabase Auth."""
    return jsonify(
        supabaseUrl=os.environ["SUPABASE_URL"],
        supabaseAnonKey=os.environ["SUPABASE_ANON_KEY"],
    )


@app.get("/healthz")
def healthz():
    return jsonify(ok=True)


# --- API ---------------------------------------------------------------------


@app.get("/plans")
@require_auth
def list_plans():
    return jsonify(plans=repo.list_plans(g.token))


@app.get("/me/plan")
@require_auth
def get_my_plan():
    ctx = load_context()
    if ctx is None:
        return jsonify(plan=None)
    prog, _ = build_progress(ctx, client_today())
    return jsonify(prog)


@app.post("/me/plan")
@require_auth
def choose_plan():
    body = request.get_json(silent=True) or {}
    plan_id = body.get("plan_id")
    if not isinstance(plan_id, int) or isinstance(plan_id, bool):
        return error("Pick a recovery plan.", 400)
    if repo.get_plan(g.token, plan_id) is None:
        return error("That plan does not exist.", 404)
    today = client_today()
    repo.save_user_plan(g.token, g.user_id, plan_id, today.isoformat())
    prog, _ = build_progress(load_context(), today)
    return jsonify(prog), 201


@app.get("/today")
@require_auth
def get_today():
    ctx = load_context()
    if ctx is None:
        return error("Choose a recovery plan first.", 409, code="no_plan")
    return jsonify(today_payload(ctx, client_today()))


@app.post("/today/steps/<int:step_id>/complete")
@require_auth
def complete_step(step_id):
    ctx = load_context()
    if ctx is None:
        return error("Choose a recovery plan first.", 409, code="no_plan")
    today = client_today()
    target = next((s for s in ctx["steps"] if s["id"] == step_id), None)
    if target is None:
        return error("That step is not part of your current level.", 404)

    _, summary = build_progress(ctx, today)
    done = summary["done_today"]
    if step_id not in done:
        earlier = [s for s in ctx["steps"] if s["position"] < target["position"]]
        if any(s["id"] not in done for s in earlier):
            return error("Finish the earlier steps first.", 409, code="locked")
        repo.add_completion(g.token, g.user_id, step_id, today.isoformat())
    return jsonify(today_payload(ctx, today))


@app.post("/me/plan/advance")
@require_auth
def advance_phase():
    body = request.get_json(silent=True) or {}
    ctx = load_context()
    if ctx is None:
        return error("Choose a recovery plan first.", 409, code="no_plan")
    if ctx["user_plan"]["finished"]:
        return error("You already finished this plan.", 409, code="finished")

    today = client_today()
    prog, _ = build_progress(ctx, today)
    min_days = ctx["phase"]["min_days"]
    if prog["days_completed"] < min_days:
        left = min_days - prog["days_completed"]
        return error(
            f"Complete {left} more full day{'s' if left != 1 else ''} first.",
            409,
            days_completed=prog["days_completed"],
            min_days=min_days,
        )
    if body.get("confirmed") is not True:
        return error(
            "Confirm that you checked with your physical therapist or doctor.", 400
        )

    phase = ctx["phase"]
    from_phase = {"number": phase["phase_number"], "name": phase["name"]}
    if prog["is_last_phase"]:
        repo.update_user_plan(g.token, g.user_id, finished=True)
        to_phase = None
    else:
        nxt = ctx["phases"][ctx["phases"].index(phase) + 1]
        repo.update_user_plan(
            g.token,
            g.user_id,
            phase_number=nxt["phase_number"],
            phase_started_on=today.isoformat(),
        )
        to_phase = {"number": nxt["phase_number"], "name": nxt["name"]}

    new_prog, _ = build_progress(load_context(), today)
    return jsonify(
        advanced=True,
        finished=to_phase is None,
        from_phase=from_phase,
        to_phase=to_phase,
        progress=new_prog,
    )


@app.delete("/me")
@require_auth
def delete_me():
    repo.delete_account(g.token)
    return "", 204


if __name__ == "__main__":
    app.run(debug=True)
