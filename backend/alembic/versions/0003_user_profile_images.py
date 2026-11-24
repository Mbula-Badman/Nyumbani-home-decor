"""add profile image URLs to users

Revision ID: 0003_user_profile_images
Revises: 0002_user_roles
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_user_profile_images"
down_revision = "0002_user_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_image_url")
