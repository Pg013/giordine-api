"""move foto_url de perfis_alunos para usuarios

Revision ID: c7d8e9f0a1b2
Revises: a1b2c3d4e5f6
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Adiciona foto_url em usuarios (nullable, sem default — preserva NULL onde nunca houve foto)
    op.add_column('usuarios', sa.Column('foto_url', sa.String(), nullable=True))

    # 2) Copia foto_url existente de perfis_alunos para usuarios
    op.execute("""
        UPDATE usuarios u
        SET foto_url = p.foto_url
        FROM perfis_alunos p
        WHERE p.usuario_id = u.id
          AND p.foto_url IS NOT NULL
    """)

    # 3) Remove foto_url de perfis_alunos (dado já foi copiado)
    op.drop_column('perfis_alunos', 'foto_url')


def downgrade() -> None:
    # 1) Recria foto_url em perfis_alunos
    op.add_column('perfis_alunos', sa.Column('foto_url', sa.String(), nullable=True))

    # 2) Copia de volta — só para alunos (perfis_alunos existe apenas para role=aluno)
    op.execute("""
        UPDATE perfis_alunos p
        SET foto_url = u.foto_url
        FROM usuarios u
        WHERE p.usuario_id = u.id
          AND u.foto_url IS NOT NULL
    """)

    # 3) Remove foto_url de usuarios
    op.drop_column('usuarios', 'foto_url')
