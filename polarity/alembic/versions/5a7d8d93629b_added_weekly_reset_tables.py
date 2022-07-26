"""Added weekly reset tables

Revision ID: 5a7d8d93629b
Revises: 6198b20f6e44
Create Date: 2022-07-26 01:05:03.809891

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5a7d8d93629b"
down_revision = "6198b20f6e44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weeklyresetautopostchannel",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.BigInteger(), nullable=False),
        sa.Column("last_msg_id", sa.BigInteger(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "weeklyresetpostsettings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "autoannounce_enabled", sa.Boolean(), server_default="t", nullable=False
        ),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("post_url", sa.String(), nullable=False),
        sa.Column("url_redirect_target", sa.String(), nullable=True),
        sa.Column("url_last_modified", sa.DateTime(), nullable=True),
        sa.Column("url_last_checked", sa.DateTime(), nullable=True),
        sa.Column("url_watcher_armed", sa.Boolean(), server_default="f", nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("weeklyresetpostsettings")
    op.drop_table("weeklyresetautopostchannel")
