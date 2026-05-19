"""add submissoes e rascunhos (Mini-fatia 2)

Cria infraestrutura de submissão do aluno:
- Enum status_submissao_enum (submitted | reviewed)
- Tabela submissoes (com UNIQUE PARCIAL em eh_repeticao=false)
- Tabela rascunhos_submissao (autosave)

Revision ID: e5b6c7d8e9f0
Revises: d4a7b3e9c2f1
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e5b6c7d8e9f0'
down_revision: Union[str, None] = 'd4a7b3e9c2f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Criar enum status_submissao
    status_submissao_enum = postgresql.ENUM(
        'submitted', 'reviewed',
        name='status_submissao_enum',
        create_type=False,
    )
    status_submissao_enum.create(op.get_bind(), checkfirst=False)

    # 2) Tabela submissoes
    op.create_table(
        'submissoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tarefa_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('respostas', postgresql.JSONB(), nullable=False),
        sa.Column(
            'status',
            status_submissao_enum,
            server_default='submitted',
            nullable=False,
        ),
        sa.Column(
            'submetido_em',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column('tempo_gasto_seg', sa.Integer(), nullable=True),
        sa.Column(
            'atrasada',
            sa.Boolean(),
            server_default='false',
            nullable=False,
        ),
        sa.Column(
            'eh_repeticao',
            sa.Boolean(),
            server_default='false',
            nullable=False,
        ),
        sa.Column('auto_score', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['tarefa_id'], ['tarefas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_submissoes_id', 'submissoes', ['id'])
    op.create_index('ix_submissoes_tarefa_id', 'submissoes', ['tarefa_id'])
    op.create_index('ix_submissoes_aluno_id', 'submissoes', ['aluno_id'])

    # UNIQUE parcial: só 1 submissão original (eh_repeticao=false) por (tarefa, aluno).
    # Repetições futuras (Fase 6 - reciclagem 50%) podem ter múltiplas linhas.
    op.create_index(
        'uq_submissoes_original',
        'submissoes',
        ['tarefa_id', 'aluno_id'],
        unique=True,
        postgresql_where=sa.text('eh_repeticao = false'),
    )

    # 3) Tabela rascunhos_submissao
    op.create_table(
        'rascunhos_submissao',
        sa.Column('tarefa_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('respostas', postgresql.JSONB(), nullable=False),
        sa.Column('progresso', postgresql.JSONB(), nullable=True),
        sa.Column(
            'atualizado_em',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['tarefa_id'], ['tarefas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tarefa_id', 'aluno_id'),
    )


def downgrade() -> None:
    op.drop_table('rascunhos_submissao')
    op.drop_index('uq_submissoes_original', table_name='submissoes')
    op.drop_index('ix_submissoes_aluno_id', table_name='submissoes')
    op.drop_index('ix_submissoes_tarefa_id', table_name='submissoes')
    op.drop_index('ix_submissoes_id', table_name='submissoes')
    op.drop_table('submissoes')
    op.execute('DROP TYPE status_submissao_enum')
