"""add comunicados_lidos

Revision ID: b5c2d1e8f3a9
Revises: 7c4e8f2a9b1d
Create Date: 2026-05-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5c2d1e8f3a9'
down_revision: Union[str, None] = '7c4e8f2a9b1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comunicados_lidos',
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('comunicado_id', sa.Integer(), nullable=False),
        sa.Column('lido_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['comunicado_id'], ['comunicados.id']),
        sa.PrimaryKeyConstraint('aluno_id', 'comunicado_id'),
    )


def downgrade() -> None:
    op.drop_table('comunicados_lidos')
