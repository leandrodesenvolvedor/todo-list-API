"""Enumerações do domínio.

Os valores válidos de status e prioridade vão ser consumidos em três lugares
diferentes: no `default` das colunas (Dia 3), no `case` que ordena por
prioridade (Dia 4) e na validação da entrada da API (Dia 6). Escritos como
texto solto, acrescentar uma prioridade nova exigiria lembrar dos três — e
esquecer um deles é um defeito que só aparece em produção. Definidos aqui,
têm um único lugar de verdade.

Herdar de `str` faz cada membro se comportar como o próprio texto — o que
permite gravá-lo em uma coluna `String`, compará-lo com uma string vinda do
banco e serializá-lo em JSON sem conversão manual.
"""

from enum import Enum


class StatusTarefa(str, Enum):
    """Situação em que uma tarefa pode estar."""

    PENDENTE = "pendente"
    CONCLUIDA = "concluida"


class PrioridadeTarefa(str, Enum):
    """Nível de prioridade de uma tarefa, da menor para a maior."""

    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"

    @property
    def peso(self) -> int:
        """Posição na ordenação por prioridade — 0 é a mais urgente.

        Ordenar pelo texto daria "alta, baixa, media, urgente", que não é a
        ordem que o usuário espera ver. O peso existe para isso.
        """
        return _PESOS[self]

    @classmethod
    def mapa_de_pesos(cls) -> dict[str, int]:
        """Mapa `valor -> peso`, no formato que o `case()` do SQL consome."""
        return {prioridade.value: prioridade.peso for prioridade in cls}


_PESOS = {
    PrioridadeTarefa.URGENTE: 0,
    PrioridadeTarefa.ALTA: 1,
    PrioridadeTarefa.MEDIA: 2,
    PrioridadeTarefa.BAIXA: 3,
}


class CampoOrdenacao(str, Enum):
    """Campos pelos quais a listagem de tarefas pode ser ordenada.

    Os valores repetem o nome público do campo na API (camelCase), porque é
    isso que o cliente envia em `?ordenarPor=`. Como é um enum, um valor fora
    da lista passa a ser recusado com 422 — antes, o código caía
    silenciosamente na ordenação por data de criação e o cliente nunca sabia
    que seu parâmetro havia sido ignorado.
    """

    CRIADO_EM = "criadoEm"
    PRAZO = "prazo"
    PRIORIDADE = "prioridade"


class Ordem(str, Enum):
    """Sentido da ordenação."""

    ASC = "asc"
    DESC = "desc"
