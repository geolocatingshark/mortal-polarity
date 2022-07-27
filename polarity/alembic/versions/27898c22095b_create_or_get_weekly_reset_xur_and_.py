"""Create or get weekly reset, xur and daily reset settings

Revision ID: 27898c22095b
Revises: 5a7d8d93629b
Create Date: 2022-07-27 23:19:19.796226

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from polarity.weekly_reset import WeeklyResetPostSettings
from polarity.xur import XurPostSettings
from polarity.ls import LostSectorPostSettings
from sqlalchemy.orm.session import Session

# revision identifiers, used by Alembic.
revision = "27898c22095b"
down_revision = "5a7d8d93629b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    for table in [WeeklyResetPostSettings, XurPostSettings, LostSectorPostSettings]:
        with session.begin():
            if session.get(table, 0) is None:
                session.add(table(0))


def downgrade() -> None:
    pass
