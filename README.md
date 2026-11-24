# Nyumbani Home

HTML/CSS/JS storefront -> FastAPI -> PostgreSQL (SQLAlchemy + Alembic) -> M-Pesa Daraja.

## Status
- The storefront opens with an animated splash screen and dedicated landing page, followed by a responsive catalog, product photography, account sign-in/registration, account-backed checkout, and demo M-Pesa order confirmation.
- Authentication uses PBKDF2 password hashes and signed, HTTP-only session cookies. Set a strong `AUTH_SECRET` in the backend environment before deploying with `APP_ENV=production`.
- Product and order data are stored in the configured database. Seed data can be loaded repeatedly with `python seed.py`.

## Setup (PowerShell, Windows)

1. Create the database (once), then verify it:

```powershell
psql -U postgres
```
```sql
CREATE USER nyumbani_user WITH PASSWORD 'choose_a_password';
CREATE DATABASE nyumbani_home OWNER nyumbani_user;
\q
```

2. Install dependencies:

```powershell
cd nyumbani-home\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and put your real database password in `DATABASE_URL`.

3. Apply the migration and load sample data:

```powershell
alembic upgrade head
python seed.py
```

4. Run the API:

```powershell
uvicorn app.main:app --reload
```

Check `http://127.0.0.1:8000/api/health`, `/api/health/db`, `/api/products` and `/docs`.

5. Open `http://127.0.0.1:8000/` to use the storefront and API from the same origin. The account flow requires the FastAPI server; opening the HTML file directly will not connect to authentication or checkout.

## Deployment and payments
Set a unique `AUTH_SECRET` and `APP_ENV=production` in the backend environment, and configure `CORS_ORIGINS` for the deployed storefront. The current checkout records demo payments; it does not yet initiate a live Daraja transaction. Search for `TODO (CLIENT)` for the Till or Paybill configuration notes.
