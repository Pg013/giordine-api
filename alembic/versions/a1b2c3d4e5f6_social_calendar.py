"""social_calendar: cor em turmas, serie_id em aulas, tabela mensagens

Revision ID: a1b2c3d4e5f6
Revises: b5c2d1e8f3a9
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b5c2d1e8f3a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── aulas (nunca foi criada por migration anterior) ──────────────────────
    op.create_table(
        'aulas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('turma_id', sa.Integer(), nullable=True),
        sa.Column('professor_id', sa.Integer(), nullable=True),
        sa.Column('titulo', sa.String(), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('data_hora', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duracao_min', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('link_aula', sa.String(), nullable=True),
        sa.Column('serie_id', sa.String(36), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['turma_id'], ['turmas.id']),
        sa.ForeignKeyConstraint(['professor_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_aulas_id', 'aulas', ['id'])
    op.create_index('ix_aulas_serie_id', 'aulas', ['serie_id'])

    # ── presencas ────────────────────────────────────────────────────────────
    op.create_table(
        'presencas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aula_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('confirmado', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('confirmado_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['aula_id'], ['aulas.id']),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aula_id', 'aluno_id', name='uq_presenca_aula_aluno'),
    )
    op.create_index('ix_presencas_id', 'presencas', ['id'])

    # ── aulas_extra ──────────────────────────────────────────────────────────
    op.create_table(
        'aulas_extra',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('data_sugerida', sa.Date(), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pendente'),
        sa.Column('resposta_admin', sa.Text(), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_aulas_extra_id', 'aulas_extra', ['id'])

    # ── turmas: cor para o calendário ────────────────────────────────────────
    op.add_column('turmas', sa.Column('cor', sa.String(7), nullable=False, server_default='#3B82F6'))

    # ── mensagens (chat DM e grupo) ──────────────────────────────────────────
    op.create_table(
        'mensagens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('remetente_id', sa.Integer(), nullable=False),
        sa.Column('destinatario_id', sa.Integer(), nullable=True),
        sa.Column('turma_id', sa.Integer(), nullable=True),
        sa.Column('conteudo', sa.Text(), nullable=False),
        sa.Column('lida', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['remetente_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['destinatario_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['turma_id'], ['turmas.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mensagens_id', 'mensagens', ['id'])
    op.create_index('ix_mensagens_remetente_id', 'mensagens', ['remetente_id'])
    op.create_index('ix_mensagens_destinatario_id', 'mensagens', ['destinatario_id'])
    op.create_index('ix_mensagens_turma_id', 'mensagens', ['turma_id'])


def downgrade() -> None:
    op.drop_index('ix_mensagens_turma_id', table_name='mensagens')
    op.drop_index('ix_mensagens_destinatario_id', table_name='mensagens')
    op.drop_index('ix_mensagens_remetente_id', table_name='mensagens')
    op.drop_index('ix_mensagens_id', table_name='mensagens')
    op.drop_table('mensagens')

    op.drop_column('turmas', 'cor')

    op.drop_index('ix_aulas_extra_id', table_name='aulas_extra')
    op.drop_table('aulas_extra')

    op.drop_index('ix_presencas_id', table_name='presencas')
    op.drop_table('presencas')

    op.drop_index('ix_aulas_serie_id', table_name='aulas')
    op.drop_index('ix_aulas_id', table_name='aulas')
    op.drop_table('aulas')
