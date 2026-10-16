# RecoverWise

A gamified daily recovery helper for people doing rehab at home. Pick a recovery plan, get a checklist of exactly what to do today, watch how to do it, and earn XP for showing up.

> **Not medical advice.** The plans are sample routines built from reputable clinical sources. Always follow your own physical therapist or doctor.

## Why I built this

I've always wanted to help people, but I never knew how to merge that with my passion for game design. When I saw physical therapy and prosthetics moving toward technology, I started working out how to build in that space. Most basic digital recovery plans stop at simple movements like picking up boxes or a little walking. They don't cover the everyday tasks people actually need, like getting out of a car, putting on shoes, or reaching a high shelf. RecoverWise puts those tasks into the plan and uses game design to make consistency feel rewarding.

## Features

**Core**
- Sign up and log in with Supabase Auth, then choose a recovery plan: ACL tear, herniated disc, or rotator cuff tear
- A daily checklist for your current phase, in order. Each step must be checked off to unlock the next
- Two kinds of steps: **exercises** and **daily-life tasks**, each with instructions and an embedded YouTube tutorial where one exists
- Phase progression: after enough fully completed days, you confirm you're ready to move on (and are reminded to check with your PT)

**Game layer**
- 10 XP per completed step, with an XP bar
- Each day is a quest line and each phase is a named level
- **Dr. Wise**, a pixel-art doctor, congratulates you when you finish a phase
- Rewards consistency, never intensity. XP is the same no matter how hard you push

**Planned**
- Streaks with a weekly rest token, and a full-day bonus
- Skill map of everyday abilities (Stand Up, Stairs, Car Transfer)
- Badges, Dr. Wise encouragement when progress is slow, pain/stiffness check-in, reminders

## Screens

<!-- Add screenshots here -->

## Tech stack

| Layer | Tool |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Flask (Python) |
| Auth and database | Supabase (Auth + Postgres with row-level security) |
| Hosting | Render (free tier) |
| Videos | YouTube privacy-enhanced embeds (no API key) |

## How it works

1. The browser signs up and logs in directly with Supabase Auth and receives a session token.
2. The browser sends that token with every request to the Flask API.
3. Flask verifies the token, then reads and writes Postgres.

| Route | Purpose |
|---|---|
| `GET /plans` | List recovery plans for the dropdown |
| `POST /me/plan` | Save the user's plan and start Phase 1 |
| `GET /today` | Today's ordered steps with done/unlocked flags |
| `POST /today/steps/<id>/complete` | Mark a step done (rejected if an earlier step isn't done) |
| `GET /me/plan` | Current plan and phase progress |
| `POST /me/plan/advance` | Move to the next phase if the minimum days are met |

## Getting started

### Prerequisites
- Python 3.10+
- A free [Supabase](https://supabase.com) project

### Setup

```bash
git clone https://github.com/yourname/recoverwise.git
cd recoverwise
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
SUPABASE_URL=your-project-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

Run the seed SQL file in the Supabase SQL editor to create the tables and load the sample plans, then start the app:

```bash
flask run
```

Open http://localhost:5000.

## Privacy

- Supabase Auth stores your email and password. I never see or store passwords
- The app stores only your chosen plan, current phase, and daily completions. No name, diagnosis, or free-text health fields
- Row-level security means you can only read and write your own rows
- Nothing is shared or sold, and there are no analytics trackers
- A **Delete my account** button erases all of your rows
- YouTube still receives a request when a video loads

## Project status

- [ ] Flask app with `GET /plans` running locally
- [ ] Supabase login recognized by Flask
- [ ] Ordered checklist for one plan (order enforced by the backend)
- [ ] Phase progression and all three plans
- [ ] Deployed on Render
- [ ] Game layer extras, usability test, and final polish

## Credits

- Exercise videos come from licensed PT and hospital YouTube channels, credited on the site
- Dr. Wise was made with a free online pixel avatar maker
- Built as a Senior Design final project
