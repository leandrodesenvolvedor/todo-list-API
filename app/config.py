"""Configuração da aplicação, lida do ambiente.

Estratégia de banco de dados deste projeto:

| Ambiente | Banco | Como é fornecido |
|---|---|---|
| Desenvolvimento local | SQLite em arquivo | `DATABASE_URL` no arquivo `.env` |
| Produção | PostgreSQL | `DATABASE_URL` no ambiente de execução |
| Testes automatizados | SQLite em memória | `DATABASE_URL` definida pela própria suíte |

A conexão é definida por uma **única variável**: `DATABASE_URL`. Não há conjunto
separado de host, porta, usuário, senha e nome do banco. Duas razões: é assim
que as plataformas de hospedagem entregam a credencial — numa URL única — e é o
que permite trocar de banco sem alterar código.

A variável é **obrigatória**, e não tem valor padrão. A alternativa seria cair
em SQLite quando ela faltasse, o que parece conveniente e esconde um problema:
quando o padrão coincide com o valor esperado, não há como saber se o `.env` foi
lido ou se a aplicação apenas caiu no padrão. Exigir a variável torna a escolha
do banco sempre explícita, e transforma uma configuração ausente em erro na
inicialização — em vez de um banco silenciosamente diferente do pretendido.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------

#: Raiz do projeto: a pasta que contém `app/`. Calculada a partir da
#: localização deste arquivo, e não do diretório de trabalho atual.
RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent

#: Caminho absoluto para o arquivo `.env`.
#:
#: `load_dotenv()` sem argumento procura o arquivo a partir do diretório de
#: trabalho e vai subindo. O efeito colateral é cruel: rodar o mesmo comando de
#: outra pasta faz o `.env` ser ignorado em silêncio. Com o caminho explícito, o
#: resultado é o mesmo de qualquer lugar.
CAMINHO_DO_ENV = RAIZ_DO_PROJETO / ".env"


# ---------------------------------------------------------------------------
# Variáveis de ambiente
# ---------------------------------------------------------------------------

#: Carrega o `.env` localizado na raiz do projeto.
#:
#: `load_dotenv` **não** sobrescreve variáveis que já existem no ambiente.
#: Portanto uma `DATABASE_URL` definida externamente tem prioridade sobre a
#: mesma variável no `.env` — é o que garante que o valor definido pela suíte de
#: testes vença o `.env` da máquina, sem o qual rodar os testes apagaria o banco
#: de trabalho.
ENV_ENCONTRADO = load_dotenv(CAMINHO_DO_ENV)

#: Origens autorizadas a chamar a API a partir de um navegador.
ORIGENS_PADRAO = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

def normalizar_url(url: str) -> str:
    """Ajusta a URL de conexão para o formato utilizado pelo SQLAlchemy.

    Algumas plataformas fornecem URLs PostgreSQL usando:

        postgres://
        postgresql://

    O primeiro esquema o SQLAlchemy 2 não aceita mais; o segundo seleciona o
    driver antigo (psycopg2), que não é o declarado no `requirements.txt` deste
    projeto. As duas são normalizadas para:

        postgresql+psycopg://

    URLs que já trazem um driver explícito são mantidas como estão — quem
    escreveu sabe o que quer.

    Args:
        url: URL de conexão recebida do ambiente.

    Returns:
        URL de conexão normalizada.
    """
    url = url.strip()

    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Configuracao:
    """Parâmetros de execução da aplicação.

    A configuração é imutável de propósito. Alterações em tempo de execução
    podem gerar comportamentos difíceis de reproduzir.

    Attributes:
        url_banco: URL utilizada para conexão com o banco.
        origens_permitidas: origens autorizadas pelo CORS.
        echo_sql: indica se o SQLAlchemy deve exibir as consultas SQL.
    """

    url_banco: str
    origens_permitidas: tuple[str, ...] = ORIGENS_PADRAO
    echo_sql: bool = False

    @classmethod
    def do_ambiente(cls) -> Configuracao:
        """Monta a configuração a partir das variáveis de ambiente.

        `DATABASE_URL` é obrigatória. O desenvolvimento local deve fornecê-la
        pelo arquivo `.env`; produção e CI/CD podem fornecê-la diretamente como
        variável de ambiente.

        Raises:
            RuntimeError: quando `DATABASE_URL` não estiver definida.
        """
        database_url = os.getenv("DATABASE_URL", "").strip()

        if not database_url:
            raise RuntimeError(
                "A variável de ambiente DATABASE_URL não foi definida.\n"
                f"Esperado um arquivo .env em: {CAMINHO_DO_ENV}\n"
                f"Arquivo encontrado: {'sim' if ENV_ENCONTRADO else 'não'}\n"
                "Copie o .env.example para .env, ou defina DATABASE_URL no "
                "ambiente de execução da aplicação."
            )

        origens = os.getenv("ORIGENS_PERMITIDAS", "").strip()

        origens_permitidas = (
            tuple(
                origem.strip()
                for origem in origens.split(",")
                if origem.strip()
            )
            or ORIGENS_PADRAO
        )

        echo_sql = os.getenv("ECHO_SQL", "").strip().lower() in {
            "1",
            "true",
            "sim",
            "yes",
        }

        return cls(
            url_banco=normalizar_url(database_url),
            origens_permitidas=origens_permitidas,
            echo_sql=echo_sql,
        )

    @property
    def dialeto(self) -> str:
        """Retorna o dialeto do banco utilizado.

        Exemplos:

            postgresql+psycopg://... -> postgresql
            sqlite:///:memory:       -> sqlite
            mysql+pymysql://...      -> mysql
        """
        return self.url_banco.split(":", 1)[0].split("+", 1)[0]

    @property
    def banco_em_memoria(self) -> bool:
        """Informa se o banco SQLite está sendo executado em memória.

        Essa configuração é útil principalmente para testes automatizados.
        """
        return self.dialeto == "sqlite" and (
            ":memory:" in self.url_banco
            or self.url_banco == "sqlite://"
        )

    @property
    def banco_em_servidor(self) -> bool:
        """Informa se o banco está hospedado em um servidor.

        SQLite é tratado como banco local. PostgreSQL, MySQL e outros bancos de
        servidor retornam True — o que mais tarde muda as opções de conexão.
        """
        return self.dialeto != "sqlite"


# ---------------------------------------------------------------------------
# Instância global da configuração
# ---------------------------------------------------------------------------

@lru_cache
def obter_configuracao() -> Configuracao:
    """Retorna a configuração da aplicação.

    A configuração é carregada uma única vez e reutilizada durante o ciclo de
    vida do processo.
    """
    return Configuracao.do_ambiente()
