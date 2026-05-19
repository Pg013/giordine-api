"""add totp fields to usuarios

Revision ID: f1d2c3b4a5e6
Revises: e9a1c4f6b8d2
Create Date: 2026-05-19 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1d2c3b4a5e6'
down_revision: Union[str, None] = 'e9a1c4f6b8d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('totp_secret', sa.String(), nullable=True))
    op.add_column('usuarios', sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('usuarios', 'totp_enabled')
    op.drop_column('usuarios', 'totp_secret')
