"""add password_reset_tokens

Revision ID: d7e9f1a3b8c2
Revises: a1b2c3d4e5f6
Create Date: 2026-05-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd7e9f1a3b8c2'
down_revision: Union[str, None] = 'f7c8d9e0a1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('usado_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_password_reset_tokens_id', 'password_reset_tokens', ['id'])
    op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'], unique=True)
    op.create_index('ix_password_reset_tokens_usuario_id', 'password_reset_tokens', ['usuario_id'])


def downgrade() -> None:
    op.drop_index('ix_password_reset_tokens_usuario_id', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_token_hash', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_id', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
