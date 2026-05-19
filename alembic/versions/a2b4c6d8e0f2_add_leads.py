"""add leads (CRM)

Revision ID: a2b4c6d8e0f2
Revises: f1d2c3b4a5e6
Create Date: 2026-05-19 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a2b4c6d8e0f2'
down_revision: Union[str, None] = 'f1d2c3b4a5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    lead_status = sa.Enum(
        'novo', 'em_contato', 'trial', 'convertido', 'descartado',
        name='lead_status_enum',
        create_type=False,  # criado inline pelo CREATE TABLE abaixo
    )

    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('whatsapp', sa.String(), nullable=False),
        sa.Column('como_conheceu', sa.String(), nullable=True),
        sa.Column('nivel_ingles', sa.String(), nullable=True),
        sa.Column('objetivo', sa.String(), nullable=True),
        sa.Column('mensagem', sa.Text(), nullable=True),
        sa.Column('status', lead_status, nullable=False, server_default='novo'),
        sa.Column('motivo_descarte', sa.String(), nullable=True),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('lembrete_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('aluno_id', sa.Integer(), nullable=True),
        sa.Column('convertido_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_leads_id', 'leads', ['id'])
    op.create_index('ix_leads_email', 'leads', ['email'])
    op.create_index('ix_leads_status', 'leads', ['status'])
    op.create_index('ix_leads_criado_em', 'leads', ['criado_em'])


def downgrade() -> None:
    op.drop_index('ix_leads_criado_em', table_name='leads')
    op.drop_index('ix_leads_status', table_name='leads')
    op.drop_index('ix_leads_email', table_name='leads')
    op.drop_index('ix_leads_id', table_name='leads')
    op.drop_table('leads')
    sa.Enum(name='lead_status_enum').drop(op.get_bind(), checkfirst=True)
