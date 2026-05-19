"""add tarefas base (Mini-fatia 1A)

Cria infraestrutura base do módulo de tarefas:
- 3 enums postgres: categoria_tarefa, status_tarefa, cefr_level
- Tabela tarefas (entidade principal)
- 2 tabelas junction: tarefa_cefr_levels, tarefa_turmas
- Coluna cefr_level em perfis_alunos

Revision ID: d4a7b3e9c2f1
Revises: c7d8e9f0a1b2
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd4a7b3e9c2f1'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Criar enums postgres explicitamente (cefr_level_enum é usado em 2 tabelas)
    categoria_tarefa_enum = postgresql.ENUM(
        'gramatica', 'vocabulario', 'leitura', 'escrita', 'escuta', 'fala', 'traducao',
        name='categoria_tarefa_enum',
        create_type=False,
    )
    status_tarefa_enum = postgresql.ENUM(
        'draft', 'published', 'archived',
        name='status_tarefa_enum',
        create_type=False,
    )
    cefr_level_enum = postgresql.ENUM(
        'A1', 'A2', 'B1', 'B2', 'C1', 'C2',
        name='cefr_level_enum',
        create_type=False,
    )
    categoria_tarefa_enum.create(op.get_bind(), checkfirst=False)
    status_tarefa_enum.create(op.get_bind(), checkfirst=False)
    cefr_level_enum.create(op.get_bind(), checkfirst=False)

    # 2) Tabela tarefas — entidade principal
    op.create_table(
        'tarefas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('categoria', categoria_tarefa_enum, nullable=False),
        sa.Column('tipo', sa.String(), nullable=False),
        sa.Column('titulo', sa.String(), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('conteudo', postgresql.JSONB(), nullable=False),
        sa.Column('rubrica', postgresql.JSONB(), nullable=True),
        sa.Column('data_entrega', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pontos_disponiveis', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            status_tarefa_enum,
            server_default='draft',
            nullable=False,
        ),
        sa.Column('criado_por', sa.Integer(), nullable=False),
        sa.Column(
            'criado_em',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column('publicado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arquivado_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tarefas_id', 'tarefas', ['id'])
    op.create_index('ix_tarefas_categoria', 'tarefas', ['categoria'])
    op.create_index('ix_tarefas_tipo', 'tarefas', ['tipo'])
    op.create_index('ix_tarefas_status', 'tarefas', ['status'])

    # 3) Junction tarefa_cefr_levels (níveis-alvo da tarefa)
    op.create_table(
        'tarefa_cefr_levels',
        sa.Column('tarefa_id', sa.Integer(), nullable=False),
        sa.Column('cefr_level', cefr_level_enum, nullable=False),
        sa.ForeignKeyConstraint(['tarefa_id'], ['tarefas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tarefa_id', 'cefr_level'),
    )

    # 4) Junction tarefa_turmas (turmas-alvo da tarefa)
    op.create_table(
        'tarefa_turmas',
        sa.Column('tarefa_id', sa.Integer(), nullable=False),
        sa.Column('turma_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['tarefa_id'], ['tarefas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['turma_id'], ['turmas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tarefa_id', 'turma_id'),
    )

    # 5) Coluna cefr_level em perfis_alunos (nullable — registros existentes ficam NULL)
    op.add_column(
        'perfis_alunos',
        sa.Column('cefr_level', cefr_level_enum, nullable=True),
    )


def downgrade() -> None:
    # 5) Remove coluna cefr_level de perfis_alunos
    op.drop_column('perfis_alunos', 'cefr_level')

    # 4) Drop junction tarefa_turmas
    op.drop_table('tarefa_turmas')

    # 3) Drop junction tarefa_cefr_levels
    op.drop_table('tarefa_cefr_levels')

    # 2) Drop indices + tabela tarefas
    op.drop_index('ix_tarefas_status', table_name='tarefas')
    op.drop_index('ix_tarefas_tipo', table_name='tarefas')
    op.drop_index('ix_tarefas_categoria', table_name='tarefas')
    op.drop_index('ix_tarefas_id', table_name='tarefas')
    op.drop_table('tarefas')

    # 1) Drop enums (na ordem inversa)
    op.execute('DROP TYPE cefr_level_enum')
    op.execute('DROP TYPE status_tarefa_enum')
    op.execute('DROP TYPE categoria_tarefa_enum')
