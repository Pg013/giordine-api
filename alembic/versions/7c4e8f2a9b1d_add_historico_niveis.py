"""add historico_niveis

Revision ID: 7c4e8f2a9b1d
Revises: 3e7f9a2b1c8d
Create Date: 2026-05-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c4e8f2a9b1d'
down_revision: Union[str, None] = '3e7f9a2b1c8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'historico_niveis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('nivel', sa.String(), nullable=False),
        sa.Column('entrada_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_historico_niveis_id'), 'historico_niveis', ['id'], unique=False)
    op.create_index(op.f('ix_historico_niveis_aluno_id'), 'historico_niveis', ['aluno_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_historico_niveis_aluno_id'), table_name='historico_niveis')
    op.drop_index(op.f('ix_historico_niveis_id'), table_name='historico_niveis')
    op.drop_table('historico_niveis')
