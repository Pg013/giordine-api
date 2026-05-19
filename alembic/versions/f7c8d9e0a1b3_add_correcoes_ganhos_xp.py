"""add correcoes, ganhos_pontos e xp_total (Mini-fatia 3)

Cria infraestrutura de correção do professor + ganho de pontos:
- Tabela correcoes (com CHECK em score 0-100 e grade enum-like)
- Tabela ganhos_pontos (histórico permanente de XP)
- Coluna xp_total em perfis_alunos (cache denormalizado, default 0)

Revision ID: f7c8d9e0a1b3
Revises: e5b6c7d8e9f0
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f7c8d9e0a1b3'
down_revision: Union[str, None] = 'e5b6c7d8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Tabela correcoes
    op.create_table(
        'correcoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submissao_id', sa.Integer(), nullable=False),
        sa.Column('professor_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('grade', sa.String(), nullable=True),
        sa.Column('auto_score', sa.Integer(), nullable=True),
        sa.Column('rubrica_scores', postgresql.JSONB(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('inline_notes', postgresql.JSONB(), nullable=True),
        sa.Column(
            'corrigido_em',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['submissao_id'], ['submissoes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['professor_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submissao_id', name='uq_correcoes_submissao'),
        sa.CheckConstraint('score >= 0 AND score <= 100', name='ck_correcoes_score_range'),
        sa.CheckConstraint(
            "grade IS NULL OR grade IN ('A+','A','A-','B+','B','B-','C+','C','C-','D','F')",
            name='ck_correcoes_grade_valida',
        ),
    )
    op.create_index('ix_correcoes_id', 'correcoes', ['id'])

    # 2) Tabela ganhos_pontos
    op.create_table(
        'ganhos_pontos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('submissao_id', sa.Integer(), nullable=False),
        sa.Column('pontos', sa.Integer(), nullable=False),
        sa.Column(
            'criado_em',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submissao_id'], ['submissoes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ganhos_pontos_id', 'ganhos_pontos', ['id'])
    op.create_index('ix_ganhos_pontos_aluno_id', 'ganhos_pontos', ['aluno_id'])
    op.create_index('ix_ganhos_pontos_submissao_id', 'ganhos_pontos', ['submissao_id'])

    # 3) Coluna xp_total em perfis_alunos (com default 0 — não quebra registros existentes)
    op.add_column(
        'perfis_alunos',
        sa.Column('xp_total', sa.Integer(), server_default='0', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('perfis_alunos', 'xp_total')

    op.drop_index('ix_ganhos_pontos_submissao_id', table_name='ganhos_pontos')
    op.drop_index('ix_ganhos_pontos_aluno_id', table_name='ganhos_pontos')
    op.drop_index('ix_ganhos_pontos_id', table_name='ganhos_pontos')
    op.drop_table('ganhos_pontos')

    op.drop_index('ix_correcoes_id', table_name='correcoes')
    op.drop_table('correcoes')
