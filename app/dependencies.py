"""Provedores de dependência: montam os objetos que as rotas usam.

Concentrar a montagem aqui tem um efeito prático: a rota declara que precisa
de um `TarefaServico` e não sabe quantas peças existem por trás dele. Se
amanhã o serviço passar a receber um colaborador novo, muda este módulo — e
nenhuma rota.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.repositories import TarefaRepositorio, UsuarioRepositorio
from app.security import HashBcrypt, HashDeSenha
from app.services import TarefaServico, UsuarioServico


def obter_hasher() -> HashDeSenha:
    """Implementação de hash usada pela aplicação.

    Declarada como dependência — e não instanciada direto no serviço — para
    poder ser substituída nos testes por uma implementação instantânea.
    """
    return HashBcrypt()


def obter_usuario_servico(
    sessao: Session = Depends(obter_sessao),
    hasher: HashDeSenha = Depends(obter_hasher),
) -> UsuarioServico:
    """Serviço de usuários, com repositório e hasher já injetados."""
    return UsuarioServico(UsuarioRepositorio(sessao), hasher)


def obter_tarefa_servico(
    sessao: Session = Depends(obter_sessao),
) -> TarefaServico:
    """Serviço de tarefas, com os dois repositórios de que depende."""
    return TarefaServico(TarefaRepositorio(sessao), UsuarioRepositorio(sessao))
