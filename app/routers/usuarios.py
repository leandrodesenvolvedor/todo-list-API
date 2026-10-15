"""Endpoints de usuário: cadastro, login e consulta.

Compare com a versão anterior: não há consulta ao banco, não há `if` de regra
de negócio e não há `raise HTTPException`. A rota traduz HTTP em uma chamada de
serviço e devolve o resultado. Os erros de negócio sobem como exceções de
domínio e são convertidos em código de status por `main.py`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import obter_usuario_servico
from app.schemas import UsuarioCreate, UsuarioLogin, UsuarioOut
from app.services import UsuarioServico

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post(
    "",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário",
    responses={409: {"description": "E-mail já cadastrado"}},
)
def cadastrar_usuario(
    dados: UsuarioCreate,
    servico: Annotated[UsuarioServico, Depends(obter_usuario_servico)],
) -> UsuarioOut:
    """Cadastra um novo usuário com a senha armazenada como hash."""
    return servico.cadastrar(dados.nome, dados.email, dados.senha)


@router.post(
    "/login",
    response_model=UsuarioOut,
    summary="Autenticar usuário",
    responses={401: {"description": "E-mail ou senha inválidos"}},
)
def autenticar_usuario(
    dados: UsuarioLogin,
    servico: Annotated[UsuarioServico, Depends(obter_usuario_servico)],
) -> UsuarioOut:
    """Confere e-mail e senha e devolve os dados do usuário."""
    return servico.autenticar(dados.email, dados.senha)


@router.get(
    "/{usuario_id}",
    response_model=UsuarioOut,
    summary="Consultar usuário",
    responses={404: {"description": "Usuário não encontrado"}},
)
def buscar_usuario(
    usuario_id: int,
    servico: Annotated[UsuarioServico, Depends(obter_usuario_servico)],
) -> UsuarioOut:
    """Retorna os dados públicos de um usuário."""
    return servico.buscar(usuario_id)
