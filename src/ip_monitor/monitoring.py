"""script monitoring.

écrit en bash le 23 octobre 2010
Dernière mise à jour (bash) le 6 mai 2024
Faute avouée, à moitié pardonnée, le plus gros de la conversion en Python
a été fait par ChatGPT les 3 et 4 juin 2024
Dernière mise à jour le 13 septembre 2024
"""
# PYTHON_ARGCOMPLETE_OK

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime
from http import client as http_client
from pathlib import Path
from sqlite3 import Row as Sqlite3Row
from typing import TYPE_CHECKING

import aiosqlite
import argcomplete
from aiohttp import ClientError, ClientSession, ClientTimeout, TCPConnector

from .config import DEFAULT_CONFIG_PATH, load_config

if TYPE_CHECKING:
    from .config import Config, IpInfo, UrlInfo
from .notify import notify

# Gestion des arguments de ligne de commande
parser: argparse.ArgumentParser = argparse.ArgumentParser(
    description="Monitoring de connexions"
)
parser.add_argument(
    "-c",
    "--config",
    # metavar="configuration_file",
    help="Le fichier de configuration à utiliser",
    default=DEFAULT_CONFIG_PATH,
)
parser.add_argument(
    "-l",
    "--log-level",
    help="Défini le niveau de journalisation",
    dest="log_level",
    metavar="log_level",
    default="WARNING",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
)

# Options de performance et de robustesse
parser.add_argument(
    "--precheck-timeout",
    type=float,
    default=None,
    help="Timeout (s) de la pré-vérification Internet (ping 1.1.1.1).",
)
parser.add_argument(
    "--precheck-enabled",
    dest="precheck_enabled",
    action="store_true",
    default=None,
    help="Active la pré-vérification Internet (par défaut: activée).",
)
parser.add_argument(
    "--no-precheck",
    dest="precheck_enabled",
    action="store_false",
    default=None,
    help="Désactive la pré-vérification Internet.",
)
parser.add_argument(
    "--ping-timeout",
    type=float,
    default=None,
    help="Timeout (s) d'un ping d'IP surveillée.",
)
parser.add_argument(
    "--http-timeout",
    type=float,
    default=None,
    help="Timeout HTTP total (s) pour les vérifications d'URL.",
)
parser.add_argument(
    "--http-connector-limit",
    type=int,
    default=None,
    help="Nombre maximum de connexions simultanées HTTP.",
)
parser.add_argument(
    "--concurrency",
    type=int,
    default=None,
    help="Nombre maximum de vérifications concurrentes (IP + URL).",
)

# Options d'affichage utilisateur
parser.add_argument(
    "--quiet",
    dest="quiet",
    action="store_true",
    default=None,
    help="Désactive les messages de progression sur la sortie standard.",
)
parser.add_argument(
    "--no-quiet",
    dest="quiet",
    action="store_false",
    default=None,
    help="Force l'affichage des messages de progression (par défaut).",
)


def _env_float(name: str) -> float | None:
    """Retourne la valeur float d'une variable d'environnement si valide."""
    val = os.getenv(name)
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        logging.warning("Variable d'environnement %s invalide: %r", name, val)
        return None


def _env_int(name: str) -> int | None:
    """Retourne la valeur int d'une variable d'environnement si valide."""
    val = os.getenv(name)
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        logging.warning("Variable d'environnement %s invalide: %r", name, val)
        return None


def _env_bool(name: str) -> bool | None:
    """Interprète une variable d'environnement booléenne (1/0, true/false…)."""
    val = os.getenv(name)
    if val is None:
        return None
    v = val.strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return True
    if v in {"0", "false", "no", "off"}:
        return False
    logging.warning("Variable d'environnement %s invalide: %r", name, val)
    return None


def _resolve_params(
    arguments: argparse.Namespace, config: Config
) -> tuple[float, float, float, int, int, bool]:
    """Compute effective parameters (CLI > ENV > YAML)."""
    precheck_timeout = (
        arguments.precheck_timeout
        if arguments.precheck_timeout is not None
        else (_env_float("IPM_PRECHECK_TIMEOUT") or config.precheck_timeout)
    )
    ping_timeout = (
        arguments.ping_timeout
        if arguments.ping_timeout is not None
        else (_env_float("IPM_PING_TIMEOUT") or config.ping_timeout)
    )
    http_timeout = (
        arguments.http_timeout
        if arguments.http_timeout is not None
        else (_env_float("IPM_HTTP_TIMEOUT") or config.http_timeout)
    )
    http_connector_limit = (
        arguments.http_connector_limit
        if arguments.http_connector_limit is not None
        else (
            _env_int("IPM_HTTP_CONNECTOR_LIMIT") or config.http_connector_limit
        )
    )
    concurrency = (
        arguments.concurrency
        if arguments.concurrency is not None
        else (_env_int("IPM_CONCURRENCY") or config.concurrency)
    )
    env_pre = _env_bool("IPM_PRECHECK_ENABLED")
    precheck_enabled = (
        arguments.precheck_enabled
        if arguments.precheck_enabled is not None
        else (env_pre if env_pre is not None else config.precheck_enabled)
    )
    return (
        float(precheck_timeout),
        float(ping_timeout),
        float(http_timeout),
        int(http_connector_limit),
        int(concurrency),
        bool(precheck_enabled),
    )


async def _precheck_internet(
    precheck_timeout: float, *, quiet: bool = False
) -> bool:
    """Ping 1.1.1.1; affiche un message utilisateur si échec."""
    logging.info("Pré-vérification (ping) de 1.1.1.1")
    if not quiet:
        print("Vérification Internet…", end=" ")
    try:
        if not await asyncio.wait_for(
            ping("1.1.1.1"), timeout=precheck_timeout
        ):
            print("Pas de connexion à Internet.")
            return False
    except Exception:
        logging.exception("Pré-vérification échouée")
        print("Pas de connexion à Internet.")
        return False
    if not quiet:
        print("OK")
    return True


@dataclass
class RuntimeParams:
    """Runtime tuning parameters used for checks."""

    http_timeout: float
    http_connector_limit: int
    concurrency: int
    ping_timeout: float
    quiet: bool = False


async def _run_all_checks(
    conn: aiosqlite.Connection,
    config: Config,
    params: RuntimeParams,
) -> tuple[list[str], list[str]]:
    """Exécute toutes les vérifications et envoie les notifications."""
    down: list[str] = []
    up: list[str] = []

    current_ips: set[str] = {ip_info.ip for ip_info in config.ips}
    current_urls: set[str] = {url_info.url for url_info in config.urls}
    await remove_old_entries(conn, current_ips, current_urls)

    timeout = ClientTimeout(total=params.http_timeout)
    connector = TCPConnector(limit=params.http_connector_limit)
    async with ClientSession(timeout=timeout, connector=connector) as session:
        sem = asyncio.Semaphore(params.concurrency)

        async def sem_task(coro: Awaitable[None]) -> None:
            async with sem:
                return await coro

        tasks: list[asyncio.Task[None]] = []

        async def run_ip(ip: IpInfo) -> None:
            if not params.quiet:
                print(f"IP {ip.ip} — {ip.description}: démarré")
            return await check_ip(conn, ip, down, up, params.ping_timeout)

        async def run_url(url: UrlInfo) -> None:
            if not params.quiet:
                print(f"URL {url.url} — {url.description}: démarré")
            return await check_url_status(conn, session, url, down, up)

        for ip in config.ips:
            tasks.append(asyncio.create_task(sem_task(run_ip(ip))))
        for url in config.urls:
            tasks.append(asyncio.create_task(sem_task(run_url(url))))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logging.exception("Tâche en erreur", exc_info=r)

        await conn.commit()

        date = datetime.now().strftime("%a %d/%m/%Y à %R")
        if down:
            message = f"Erreur monitoring sur {', '.join(down)} le {date}"
            await notify(session, config, message)
        if up:
            message = f"{', '.join(up)} de nouveau up depuis le {date}"
            await notify(session, config, message)

        if not params.quiet:
            print(f"Terminé: {len(down)} down, {len(up)} up.")

    return down, up


async def init_db(db_path: Path) -> aiosqlite.Connection:
    """Ouvre et initialise la BDD."""
    conn: aiosqlite.Connection = await aiosqlite.connect(db_path)
    await conn.execute("""CREATE TABLE IF NOT EXISTS status (
                          id INTEGER PRIMARY KEY,
                          type TEXT NOT NULL,
                          address TEXT NOT NULL,
                          down INTEGER NOT NULL,
                          UNIQUE(type, address)
                          )""")
    return conn


async def update_status(
    conn: aiosqlite.Connection, addr_type: str, address: str, is_down: int
) -> None:
    """Met à jour le statut d'une IP ou URL."""
    logging.debug(
        "Mise à jour de l'adresse %s, type %s down : %i",
        address,
        addr_type,
        is_down,
    )
    await conn.execute(
        """
        INSERT INTO status(type, address, down)
        VALUES (?, ?, ?)
        ON CONFLICT(type, address) DO UPDATE
          SET down = excluded.down
        """,
        (addr_type, address, is_down),
    )


async def check_status(
    conn: aiosqlite.Connection, addr_type: str, address: str
) -> bool:
    """Vérifie le statut d'une adresse.

    Retourne True si down, sinon False
    """
    logging.debug("Vérification de %s de type %s", address, addr_type)
    async with conn.execute(
        "SELECT down FROM status WHERE type=? AND address=?",
        (addr_type, address),
    ) as cursor:
        row: Sqlite3Row | None = await cursor.fetchone()
        logging.debug("Résultat : %s", row)
        return row is not None and row[0] == 1


async def remove_old_entries(
    conn: aiosqlite.Connection,
    current_ips: set[str],
    current_urls: set[str],
) -> None:
    """Nettoie les adresses à ne plus surveiller."""
    logging.info("Nettoyage des adresses")
    logging.debug("Addresses IP : %s", current_ips)
    logging.debug("Adresses URL : %s", current_urls)
    # 1) Suppression des IP obsolètes
    if current_ips:
        # Génère "?, ?, ?" selon le nombre d'IPs
        placeholders = ",".join("?" for _ in current_ips)
        await conn.execute(
            f"""
            DELETE FROM status
            WHERE type = 'IP'
              AND address NOT IN ({placeholders})
            """,
            tuple(current_ips),
        )
    else:
        # Pas d'IP à conserver → supprimer toutes les lignes IP
        await conn.execute("DELETE FROM status WHERE type = 'IP'")

    # 2) Suppression des URLs obsolètes
    if current_urls:
        placeholders = ",".join("?" for _ in current_urls)
        await conn.execute(
            f"""
            DELETE FROM status
            WHERE type = 'URL'
              AND address NOT IN ({placeholders})
            """,
            tuple(current_urls),
        )
    else:
        await conn.execute("DELETE FROM status WHERE type = 'URL'")


async def ping(ip: str) -> bool:
    """Ping une IP."""
    logging.debug("Ping adresse IP %s", ip)
    # Forcer la locale en C pour une sortie stable, même si on s'appuie
    # principalement sur le code de retour (0: au moins une réponse)
    env = os.environ.copy()
    env.setdefault("LC_ALL", "C")
    env.setdefault("LANG", "C")
    proc = await asyncio.create_subprocess_exec(
        "ping",
        "-q",
        "-s26",
        "-c5",
        ip,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )
    stdout, stderr = await proc.communicate()
    logging.debug("Code retour ping: %s", proc.returncode)
    if stdout:
        logging.debug("Sortie ping brute :\n%s", stdout.decode(errors="ignore"))
    # iputils ping: 0 = au moins une réponse, 1 = aucune réponse, 2 = erreur
    return proc.returncode == 0


async def check_url(session: ClientSession, url: str) -> bool:
    """Vérifie si une URL est down."""
    try:
        target = (
            url if url.startswith(("http://", "https://")) else f"http://{url}"
        )
        async with session.head(target, allow_redirects=True) as response:
            if response.status == http_client.OK:
                return True

        async with session.get(target, allow_redirects=True) as response:
            return response.status == http_client.OK

    except ClientError:
        return False


async def check_ip(
    conn: aiosqlite.Connection,
    ip: IpInfo,
    down: list[str],
    up: list[str],
    ping_timeout: float,
) -> None:
    """Vérifie une IP et la place dans la bonne liste."""
    logging.info("Vérification (ping) de %s", ip.ip)
    try:
        is_up = await asyncio.wait_for(ping(ip.ip), timeout=ping_timeout)
    except Exception:
        logging.exception("Erreur pendant le ping de %s", ip.ip)
        is_up = False
    if not is_up:
        if not await check_status(conn, "IP", ip.ip):
            logging.info("%s down", ip.ip)
            down.append(ip.description)
            logging.info("Ajout %s aux IP down dans la base de données", ip.ip)
            await update_status(conn, "IP", ip.ip, 1)
    elif await check_status(conn, "IP", ip.ip):
        logging.info("%s à nouveau up", ip.ip)
        up.append(ip.description)
        logging.debug("Ajout de %s en base comme up", ip.ip)
        await update_status(conn, "IP", ip.ip, 0)


async def check_url_status(
    conn: aiosqlite.Connection,
    session: ClientSession,
    url_info: UrlInfo,
    down: list[str],
    up: list[str],
) -> None:
    """Vérifie si une URL est joignable et la place dans la bonne liste."""
    logging.info("Vérification de l'URL %s", url_info.url)
    if not await check_url(session, url_info.url):
        if not await check_status(conn, "URL", url_info.url):
            down.append(url_info.description)
            await update_status(conn, "URL", url_info.url, 1)
    elif await check_status(conn, "URL", url_info.url):
        up.append(url_info.description)
        await update_status(conn, "URL", url_info.url, 0)


async def main() -> None:
    """Fonction principale."""
    argcomplete.autocomplete(parser)
    arguments = parser.parse_args()
    logging.basicConfig(
        level=arguments.log_level,
        format="%(asctime)s (%(levelname)s) [%(name)s] %(message)s",
    )
    config_file = os.path.abspath(os.path.join(os.getcwd(), arguments.config))
    if not os.path.exists(config_file):
        print(
            f"{config_file} : Le fichier de configuration spécifié n'existe pas.",
            file=sys.stderr,
        )
        sys.exit(1)
    elif not os.access(config_file, os.R_OK):
        print(
            f"Impossible de lire {config_file} : permission non accordée.",
            file=sys.stderr,
        )
        sys.exit(1)
    config: Config = await load_config(config_file)

    (
        precheck_timeout,
        ping_timeout,
        http_timeout,
        http_connector_limit,
        concurrency,
        precheck_enabled,
    ) = _resolve_params(arguments, config)

    # Quiet: CLI > ENV > default(False) — be tolerant if attribute is missing
    env_quiet = _env_bool("IPM_QUIET")
    arg_quiet = getattr(arguments, "quiet", None)
    quiet = (
        arg_quiet
        if arg_quiet is not None
        else (env_quiet if env_quiet is not None else False)
    )

    if not quiet:
        print(
            f"Config: {config_file} — IPs: {len(config.ips)}, URLs: {len(config.urls)}, "
            f"concurrency: {concurrency}"
        )

    if precheck_enabled:
        ok = await _precheck_internet(precheck_timeout, quiet=quiet)
        if not ok:
            return

    conn: aiosqlite.Connection | None = None
    try:
        conn = await init_db(config.db_path)

        await _run_all_checks(
            conn,
            config,
            RuntimeParams(
                http_timeout=http_timeout,
                http_connector_limit=http_connector_limit,
                concurrency=concurrency,
                ping_timeout=ping_timeout,
                quiet=quiet,
            ),
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info("Interruption demandée, arrêt en cours…")
        raise
    except Exception:
        logging.exception("Erreur inattendue dans main()")
    finally:
        if conn is not None:
            try:
                await conn.close()
            except Exception:
                logging.exception("Erreur à la fermeture de la base")
