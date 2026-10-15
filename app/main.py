"""Ponto de entrada: cria o app, registra as rotas e traduz erros em HTTP."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import obter_configuracao
from app.database import criar_tabelas
from app.exceptions import (
    AcessoNaoAutorizado,
    CredenciaisInvalidas,
    EmailJaCadastrado,
    ErroDeDominio,
    RecursoNaoEncontrado,
    RegraDeNegocioViolada,
)
from app.routers import usuarios, tarefas

# Cada família de erro de domínio corresponde a um código HTTP. A ordem
# importa: vale o primeiro tipo que casar, do mais específico ao mais geral.
STATUS_POR_ERRO: tuple[tuple[type[ErroDeDominio], int], ...] = (
    (RecursoNaoEncontrado, 404),
    (EmailJaCadastrado, 409),
    (CredenciaisInvalidas, 401),
    (AcessoNaoAutorizado, 403),
    (RegraDeNegocioViolada, 422),
    (ErroDeDominio, 400),
)


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
    """Prepara o banco na subida da aplicação e libera recursos na descida."""
    criar_tabelas()
    yield


app = FastAPI(
    title="Todo List API",
    description=(
        "Backend de gerenciamento de tarefas. "
        "Projeto Integrador da UC 12 — Técnico em Informática, SENAC Minas."
    ),
    version="2.1.0",
    lifespan=ciclo_de_vida,
)


app.include_router(usuarios.router)
app.include_router(tarefas.router)



@app.get("/", tags=["Status"], summary="Verificar se a API está no ar")
def raiz() -> dict[str, str]:
    """Confirma que a API está no ar e indica onde está a documentação."""
    return {"mensagem": "Todo List API no ar", "documentacao": "/docs"}
