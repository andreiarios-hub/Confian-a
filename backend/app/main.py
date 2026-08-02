import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .database import Base, engine
from .routers import relatorios, servicos

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Criação automática de tabelas — suficiente para dev/SQLite. Em
    # produção com Postgres/Supabase, considere migrar para Alembic.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Confiança Depósito e Armazenamento — API",
    description="API REST para gestão de ordens de serviço de depósito judiciário.",
    version="1.0.0",
    lifespan=lifespan,
)

_origens_env = os.getenv("CORS_ORIGINS", "*").strip()
_origens = ["*"] if _origens_env == "*" else [o.strip() for o in _origens_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens,
    # allow_credentials com allow_origins=["*"] é inválido pela spec de CORS.
    allow_credentials=_origens != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def tratar_erro_banco(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"detail": "Erro ao acessar o banco de dados."})


@app.exception_handler(ValueError)
async def tratar_erro_validacao(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/", tags=["Status"])
def raiz():
    return {"status": "ok", "servico": "Confiança Depósito e Armazenamento API"}


app.include_router(servicos.router)
app.include_router(relatorios.router)
