"""
Script para criar o usuário admin inicial.
Uso: python -m app.scripts.create_admin
"""
from app.database import SessionLocal
from app.models.usuario import Usuario, RoleEnum
from app.models.perfil_aluno import PerfilAluno
from app.utils.security import get_password_hash


def main() -> None:
    print("=== Criar Admin Inicial ===\n")
    nome = input("Nome completo: ").strip()
    username = input("Username: ").strip()
    email = input("E-mail: ").strip()
    senha = input("Senha: ").strip()

    if not all([nome, username, email, senha]):
        print("\nErro: todos os campos são obrigatórios.")
        return

    db = SessionLocal()
    try:
        if db.query(Usuario).filter(Usuario.email == email).first():
            print(f"\nErro: já existe um usuário com o e-mail '{email}'.")
            return

        if db.query(Usuario).filter(Usuario.username == username).first():
            print(f"\nErro: já existe um usuário com o username '{username}'.")
            return

        usuario = Usuario(
            nome=nome,
            username=username,
            email=email,
            senha_hash=get_password_hash(senha),
            role=RoleEnum.admin,
            ativo=True,
        )
        db.add(usuario)
        db.flush()

        perfil = PerfilAluno(
            usuario_id=usuario.id,
            acesso_liberado=True,
        )
        db.add(perfil)
        db.commit()
        db.refresh(usuario)

        print("\n[OK] Admin criado com sucesso!")
        print(f"  ID:       {usuario.id}")
        print(f"  Nome:     {usuario.nome}")
        print(f"  Username: {usuario.username}")
        print(f"  E-mail:   {usuario.email}")
        print(f"  Role:     {usuario.role.value}")

    except Exception as exc:
        db.rollback()
        print(f"\nErro ao criar admin: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
