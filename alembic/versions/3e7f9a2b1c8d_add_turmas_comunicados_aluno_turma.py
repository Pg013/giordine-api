"""add turmas comunicados aluno_turma

Revision ID: 3e7f9a2b1c8d
Revises: 6f3d24cda29a
Create Date: 2026-05-15 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3e7f9a2b1c8d'
down_revision: Union[str, None] = '6f3d24cda29a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'turmas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('nivel', sa.String(), nullable=False),
        sa.Column('professor_id', sa.Integer(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['professor_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_turmas_id'), 'turmas', ['id'], unique=False)

    op.create_table(
        'aluno_turma',
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('turma_id', sa.Integer(), nullable=False),
        sa.Column('entrada_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['turma_id'], ['turmas.id']),
        sa.PrimaryKeyConstraint('aluno_id', 'turma_id'),
    )

    op.create_table(
        'comunicados',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('autor_id', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('turma_id', sa.Integer(), nullable=True),
        sa.Column('enviado_email', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['autor_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['turma_id'], ['turmas.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_comunicados_id'), 'comunicados', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_comunicados_id'), table_name='comunicados')
    op.drop_table('comunicados')
    op.drop_table('aluno_turma')
    op.drop_index(op.f('ix_turmas_id'), table_name='turmas')
    op.drop_table('turmas')
