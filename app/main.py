from dotenv import load_dotenv
load_dotenv()  # antes de qualquer import que leia os.environ

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.alunos import router as alunos_router
from app.routers.aulas import router_aulas, router_aulas_extra
from app.routers.professores import router as professores_router
from app.routers.social import router as social_router
from app.routers.me import router as me_router
from app.routers.tarefas import router as tarefas_router
from app.routers.alunos_tarefas import router as alunos_tarefas_router
from app.routers.correcoes import router as correcoes_router
from app.routers.ranking import router as ranking_router
from app.routers.queen import router as queen_router

app = FastAPI(title="Giordine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(alunos_router)
app.include_router(router_aulas)
app.include_router(router_aulas_extra)
app.include_router(professores_router)
app.include_router(social_router)
app.include_router(me_router)
app.include_router(tarefas_router)
app.include_router(alunos_tarefas_router)
app.include_router(correcoes_router)
app.include_router(ranking_router)
app.include_router(queen_router)


@app.get("/")
def root():
    return {"status": "ok"}
