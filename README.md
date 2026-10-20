# PayoutFlow

PayoutFlow is a payout system for a creator marketplace. Creators finish jobs and earn
money, and each week the system groups those earnings into payouts.

> Payouts are simulated. No real money is moved and no payment provider is connected.

## What it does

- Works out each creator's earnings from completed jobs: tips, surge pricing and platform fee.
- Creates weekly payout batches for every creator.
- Makes sure no earning is paid twice, even when two admins act at the same time.
- Lets each creator see only their own earnings and payouts.
- Keeps an audit log of important actions.

## Tech stack

- **Backend:** Python, Django, Django REST Framework, PostgreSQL
- **Frontend:** Next.js, React, TypeScript, Tailwind CSS

## Project structure

```text
api/   Django backend (REST API)
web/   Next.js frontend
```

## Getting started

You need **Python 3.13+**, **Node 20+** and **PostgreSQL 14+**.

**1. Create the database**

```bash
createdb payout_db
```

**2. Start the backend**

```bash
cd api
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install --group dev
cp .env.example .env             # then set SECRET_KEY and DATABASE_URL
python manage.py migrate
python manage.py seed_data       # adds sample users and data
python manage.py runserver 8000
```

**3. Start the frontend** (in a new terminal)

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000 in your browser.

### Demo logins

These accounts are created by `seed_data`:

| Role    | Email                       | Password       |
|---------|-----------------------------|----------------|
| Admin   | `admin@payoutflow.local`    | `Admin!2345`   |
| Creator | `creator1@payoutflow.local` | `Creator!2345` |

### Run with Docker

```bash
cp api/.env.example api/.env
docker compose up --build
```

PostgreSQL is not included in Docker. Set `DATABASE_URL` in `api/.env` to use
`host.docker.internal` so it can reach the database on your computer.

## Running tests

```bash
cd api
pytest
ruff check .
```

## API docs

When the backend is running:

- Swagger UI: http://localhost:8000/api/docs/
- OpenAPI schema: http://localhost:8000/api/schema/
