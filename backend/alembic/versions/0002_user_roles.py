"""add client, staff, and admin roles

Revision ID: 0002_user_roles
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_user_roles"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="client"),
    )
    op.execute("UPDATE users SET role = 'admin' WHERE is_admin = TRUE")
    with op.batch_alter_table("users") as batch:
        batch.create_check_constraint("ck_users_role_valid", "role IN ('client','staff','admin')")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role_valid", type_="check")
        batch.drop_column("role")
