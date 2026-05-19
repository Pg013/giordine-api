"""add queen tables

Revision ID: e9a1c4f6b8d2
Revises: d7e9f1a3b8c2
Create Date: 2026-05-19 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e9a1c4f6b8d2'
down_revision: Union[str, None] = 'd7e9f1a3b8c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'queen_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_queen_messages_id', 'queen_messages', ['id'])
    op.create_index('ix_queen_messages_usuario_id', 'queen_messages', ['usuario_id'])
    op.create_index('ix_queen_messages_criado_em', 'queen_messages', ['criado_em'])

    op.create_table(
        'queen_training_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule', sa.String(length=500), nullable=False),
        sa.Column('criado_por_id', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['criado_por_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_queen_training_notes_id', 'queen_training_notes', ['id'])


def downgrade() -> None:
    op.drop_index('ix_queen_training_notes_id', table_name='queen_training_notes')
    op.drop_table('queen_training_notes')
    op.drop_index('ix_queen_messages_criado_em', table_name='queen_messages')
    op.drop_index('ix_queen_messages_usuario_id', table_name='queen_messages')
    op.drop_index('ix_queen_messages_id', table_name='queen_messages')
    op.drop_table('queen_messages')
