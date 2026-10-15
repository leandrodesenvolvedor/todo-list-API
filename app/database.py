"""Infraestrutura de banco: engine, fábrica de sessões e a classe Base do ORM.

Este módulo é o único lugar que sabe **qual** banco está em uso. O resto da
aplicação trabalha com a sessão do SQLAlchemy e não muda ao trocar de SQLite
para PostgreSQL — nenhum modelo, repositório, serviço ou rota precisa de ajuste.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Configuracao, obter_configuracao


def _opcoes_do_engine(configuracao: Configuracao) -> dict[str, Any]:
    """Opções de conexão adequadas ao banco em uso.

    **SQLite em memória** (testes): o banco existe apenas enquanto a conexão
    existir. Sem `StaticPool`, cada operação abriria uma conexão nova e
    encontraria um banco vazio.

    **SQLite em arquivo** (desenvolvimento): mantém o pool padrão, mas precisa de
    `check_same_thread=False`, porque o servidor atende requisições em threads
    diferentes daquela que abriu a conexão.

    **Banco em servidor** (PostgreSQL em produção): `pool_pre_ping` testa a
    conexão antes de usá-la e `pool_recycle` a renova a cada 30 minutos — os dois
    protegem contra conexões derrubadas por inatividade, que é o erro mais comum
    em banco gerenciado.
    """
    if configuracao.dialeto == "sqlite":
        opcoes: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if configuracao.banco_em_memoria:
            opcoes["poolclass"] = StaticPool
        return opcoes

    return {"pool_pre_ping": True, "pool_recycle": 1800}


@event.listens_for(Engine, "connect")
def _ativar_chaves_estrangeiras(conexao_dbapi: Any, _registro: Any) -> None:
    """Liga a verificação de chave estrangeira em cada conexão SQLite.

    O SQLite vem com essa verificação **desligada** por padrão, por
    compatibilidade histórica. Sem este ajuste, o banco de desenvolvimento
    aceitaria uma tarefa apontando para um usuário inexistente — e o mesmo código
    recusaria em produção, no PostgreSQL.

    Divergência silenciosa de comportamento entre ambientes é a categoria de
    defeito mais caro de encontrar: o teste passa na máquina de quem escreveu e
    falha só depois do deploy. Por isso a verificação é ligada aqui, e não
    deixada como responsabilidade de quem configura o ambiente.

    O `isinstance` garante que o comando só é enviado a conexões SQLite; com
    PostgreSQL, a função não faz nada.

    No Dia 1 ainda não há chave estrangeira nenhuma no projeto, então este ajuste
    não tem efeito observável. Ele é escrito agora porque pertence a este módulo;
    o efeito aparece no Dia 3, quando a `Tarefa` ganhar a chave estrangeira, e é
    testado no Dia 7.
    """
    if isinstance(conexao_dbapi, sqlite3.Connection):
        cursor = conexao_dbapi.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


_configuracao = obter_configuracao()

engine = create_engine(
    _configuracao.url_banco,
    echo=_configuracao.echo_sql,
    **_opcoes_do_engine(_configuracao),
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def criar_tabelas() -> None:
    """Cria as tabelas que ainda não existem.

    Com SQLite, o arquivo do banco é criado automaticamente na primeira conexão.
    Com PostgreSQL, o banco (a *database*) precisa existir previamente — o que
    costuma ser feito pela própria plataforma de hospedagem.

    A chamada acontece na inicialização da aplicação, e não na importação deste
    módulo: importar um módulo não deve ter efeito colateral sobre o banco.

    O import dentro da função é o que registra os modelos no `metadata` do
    SQLAlchemy. Sem ele, o `create_all` não encontra o que criar, mesmo que as
    classes existam em outro arquivo — e nenhuma tabela aparece, sem erro
    algum. É um defeito silencioso clássico, e a razão pela qual este import
    existe apesar de nada usá-lo aqui (daí o `noqa`, que impede o verificador
    de estilo de removê-lo por parecer inútil).

    Ele fica dentro da função, e não no topo do arquivo, porque `models.py`
    importa `Base` deste módulo: no topo, os dois arquivos se importariam em
    círculo e a aplicação não subiria.
    """
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def obter_sessao() -> Generator[Session, None, None]:
    """Fornece uma sessão de banco por requisição e a encerra ao final.

    Usada com `Depends(obter_sessao)` a partir do Dia 6. O `finally` garante o
    fechamento mesmo se a rota levantar uma exceção — o mesmo princípio do
    `finally` estudado na Aula 16.
    """
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()
