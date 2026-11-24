# Nyumbani Home

HTML/CSS/JS storefront -> FastAPI -> SQLite or PostgreSQL/Neon (SQLAlchemy + Alembic) -> M-Pesa Daraja.

## Status
- The storefront opens with an animated splash screen and dedicated landing page, followed by a responsive catalog, product photography, account sign-in/registration, account-backed checkout, and demo M-Pesa order confirmation.
- Authentication uses PBKDF2 password hashes and signed, HTTP-only session cookies. Set a strong `AUTH_SECRET` in the backend environment before deploying with `APP_ENV=production`.
- Client, staff, and admin accounts have separate dashboards. Admins get sales/order charts, order management, inventory/catalog tools, and team access management. Staff can process orders and edit catalog/stock. Clients can see their orders and update their profile.
- PostgreSQL URLs from Neon use psycopg 3 automatically. Local development can continue to use SQLite.
- Set `ADMIN_EMAIL` in the backend environment and run `python create_admin.py` from the backend folder to provision the administrator account. New registrations cannot claim that address or assign themselves staff/admin privileges; admins promote registered accounts to staff from the Team dashboard.
- Product and order data are stored in the configured database. Seed data can be loaded repeatedly with `python seed.py`.

## Setup (PowerShell, Windows)

1. In the [Neon Console](https://neon.com/docs/connect/connect-from-any-app), copy the pooled connection string for `DATABASE_URL` and the unpooled/direct string for `MIGRATION_DATABASE_URL`. Keep Neon's `sslmode=require` (and `channel_binding=require`, if present) parameters. The example SQLite URL can be used for local development instead. Keep both URLs in the ignored `.env` file; don't commit database credentials.

2. Install dependencies:

```powershell
cd nyumbani-home\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace `DATABASE_URL` and `MIGRATION_DATABASE_URL` with the Neon connection strings. The application automatically selects the installed psycopg 3 driver for `postgresql://` URLs. Alembic uses `MIGRATION_DATABASE_URL` when set and otherwise falls back to `DATABASE_URL`.
Set `ADMIN_EMAIL` to the email address that should own the admin dashboard.

3. Initialize the database and administrator:

```powershell
alembic upgrade head
python seed.py
python create_admin.py
```

Enter the admin name and password when prompted. A new Neon database does not automatically include data from your local SQLite database.

For a local database created by an older version before Alembic was used, back it up first. If its schema matches the `0001_initial` migration, run `alembic stamp 0001_initial` once, then `alembic upgrade head`. Do not stamp a new or incomplete database.

4. Run the API:

```powershell
uvicorn app.main:app --reload
```

Check `http://127.0.0.1:8000/api/health`, `/api/health/db`, `/api/products` and `/docs`.

5. Open `http://127.0.0.1:8000/` to use the storefront and API from the same origin. The account flow requires the FastAPI server; opening the HTML file directly will not connect to authentication or checkout.

## Deployment and payments
Set the Neon `DATABASE_URL`, a unique `AUTH_SECRET`, `ADMIN_EMAIL`, and `APP_ENV=production` in the backend environment, and configure `CORS_ORIGINS` for the deployed storefront. Run `alembic upgrade head` after pulling schema changes. The current checkout records demo payments; it does not yet initiate a live Daraja transaction. Search for `TODO (CLIENT)` for the Till or Paybill configuration notes.
