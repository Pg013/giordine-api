from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.alunos import router as alunos_router
from app.routers.aulas import router_aulas, router_aulas_extra

load_dotenv()

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


@app.get("/")
def root():
    return {"status": "ok"}
