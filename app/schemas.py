"""Schemas Pydantic: o contrato de entrada e saída da API.

Aqui mora a tradução entre dois mundos de nomenclatura. O Python escreve
`usuario_id` e `criado_em`; o JSON que o front-end consome espera `usuarioId` e
`criadoEm`. A versão anterior resolvia isso nomeando os atributos do modelo em
camelCase — ou seja, deixando a convenção do cliente vazar para dentro do
domínio.

Agora a conversão acontece **na borda**, que é o lugar dela: o domínio fala
Python idiomático e estes schemas fazem a tradução automaticamente, pelo
`alias_generator`. `populate_by_name=True` mantém a compatibilidade: a API
aceita tanto `usuarioId` quanto `usuario_id` na entrada.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from app.enums import PrioridadeTarefa, StatusTarefa


class EsquemaDeEntrada(BaseModel):
    """Base dos schemas que recebem dados do cliente."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class EsquemaDeSaida(BaseModel):
    """Base dos schemas que devolvem dados ao cliente.

    `from_attributes=True` permite devolver o objeto do modelo direto da rota:
    o Pydantic lê os atributos — inclusive os que são propriedades, como
    `status` e `concluido_em` — e monta o JSON.
    """

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


# ----------------------------------------------------------------- Usuário

class UsuarioCreate(EsquemaDeEntrada):
    """Dados recebidos no cadastro de usuário."""

    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=72)  # 72 é o limite do bcrypt


class UsuarioLogin(EsquemaDeEntrada):
    """Credenciais recebidas no login."""

    email: EmailStr
    senha: str


class UsuarioOut(EsquemaDeSaida):
    """Dados devolvidos sobre um usuário.

    Não declara a senha nem o hash — é o schema de saída que garante que eles
    nunca saiam da API, independentemente do que exista no modelo.
    """

    id: int
    nome: str
    email: EmailStr
    criado_em: datetime


# ------------------------------------------------------------------ Tarefa

class TarefaCreate(EsquemaDeEntrada):
    """Dados recebidos na criação de uma tarefa.

    O status não é aceito: toda tarefa nasce pendente (RN-02).
    """

    usuario_id: int
    titulo: str = Field(min_length=1, max_length=200)
    prioridade: PrioridadeTarefa = PrioridadeTarefa.MEDIA
    prazo: date | None = None


class TarefaUpdate(EsquemaDeEntrada):
    """Campos que podem ser alterados. Todos opcionais (atualização parcial)."""

    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    status: StatusTarefa | None = None
    prioridade: PrioridadeTarefa | None = None
    prazo: date | None = None


class TarefaOut(EsquemaDeSaida):
    """Representação completa de uma tarefa nas respostas da API."""

    id: int
    usuario_id: int
    titulo: str
    status: StatusTarefa
    prioridade: PrioridadeTarefa
    prazo: date | None
    criado_em: datetime
    atualizado_em: datetime
    concluido_em: datetime | None
