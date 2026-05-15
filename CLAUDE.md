# Giordine API — Contexto do Projeto

## Visão Geral
Backend do site do Professor Giordine (Methodology GN).
API REST construída com FastAPI + PostgreSQL (Neon) + Alembic.
Frontend em React + Vite hospedado na Vercel.

## Stack
- Python + FastAPI
- PostgreSQL via Neon (serverless)
- SQLAlchemy ORM + Alembic migrations
- JWT (access token 1h + refresh token 7 dias)
- bcrypt para hash de senhas
- Deploy: Render

## Estrutura do Projeto
- app/main.py — entry point, CORS, routers
- app/database.py — engine, SessionLocal, Base
- app/models/ — SQLAlchemy models
- app/routers/ — endpoints organizados por domínio
- app/schemas/ — Pydantic schemas
- app/utils/security.py — JWT, hash, dependencies
- alembic/ — migrations

## Banco de Dados
- Host: Neon (PostgreSQL 17, região São Paulo)
- Database: neondb
- Migrations: sempre via Alembic, nunca alterar tabelas manualmente
- Nunca usar alembic --autogenerate sem revisar o arquivo gerado

## Regras de Negócio Importantes
- Roles: 'aluno' | 'professor' | 'admin'
- Cadastro de alunos: feito APENAS pelo admin (sem registro público)
- Acesso bloqueado: perfil_aluno.acesso_liberado = false
  retorna 403 com mensagem orientando contato via WhatsApp
- Idioma do portal: automático por nível
  (básico/básico_2/básico_3 = 'pt', intermediário em diante = 'en')
- Pontuação: ciclo mensal (reseta dia 1º às 00h00)
  + histórico permanente (nunca reseta)
- Tarefas: reciclam quando aluno esgota o catálogo do nível
  (repetição vale 50% dos pontos originais)
- Migrações de nível: pontos do mês corrente são preservados

## Regras de Desenvolvimento
- NUNCA antecipe funcionalidades não solicitadas
- NUNCA altere arquivos existentes sem mostrar o diff primeiro
- NUNCA rode alembic upgrade head automaticamente — sempre perguntar
- SEMPRE perguntar antes de deletar ou sobrescrever qualquer arquivo
- SEMPRE criar migration nova para qualquer alteração de schema
- Se tiver dúvida sobre escopo, perguntar antes de agir
- Cada sessão tem escopo fechado — fazer apenas o que foi pedido

## Fases do Projeto
- Fase 1: Site público (React) ✅
- Fase 2: Backend + Auth ← ATUAL
- Fase 3: Scaffold do portal
- Fase 4: Painel Admin (Giordine)
- Fase 5: Portal do Aluno (base)
- Fase 6: Sistema de Conquistas
- Fase 7: Tarefas + Gamificação
- Fase 8: Presenças + Aula Extra
- Fase 9: Feedback + Finalização
- Fase 10: Pagamentos (futuro)

## Variáveis de Ambiente necessárias (.env)
DATABASE_URL=
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_URL=
