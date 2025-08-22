# IP Monitor

Un script asynchrone de monitoring d’adresses IP et d’URL, avec persistance SQLite et notifications via ntfy.sh ou smsbox.net. Conçu pour être robuste (timeouts, concurrence bornée, nettoyage propre) et facilement configurable via YAML, variables d’environnement et options CLI.

## Sommaire
- [Présentation rapide](#présentation-rapide)
- [Prérequis](#prérequis)
- [Installation (UV)](#installation-uv)
- [Utilisation (CLI)](#utilisation-cli)
- [Configuration YAML complète](#configuration-yaml-complète)
- [Détails de schéma et validations](#détails-de-schéma-et-validations)
- [Overrides via ENV et CLI (priorité)](#overrides-via-env-et-cli-priorité)
- [Fonctionnement interne](#fonctionnement-interne)
- [Déploiement (systemd)](#déploiement-systemd)
- [Développement](#développement)
- [Couverture de tests](#couverture-de-tests)
- [Dépannage (FAQ)](#dépannage-faq)
- [Licence](#licence)
- [Feuille de route (TODO)](#feuille-de-route-todo)

## Présentation rapide
- Surveille des IP (ICMP ping) et des URL (HTTP HEAD/GET) en parallèle.
- Persistance du statut (down/up) dans SQLite pour n’alerter que sur changements.
- Envoie des notifications via ntfy.sh ou smsbox.net.
- Timeouts et concurrence configurables (YAML/ENV/CLI), pré‑vérification Internet optionnelle.

[⬆️ Retour en haut](#ip-monitor)

## Prérequis
- Python 3.12+
- UV (gestion des dépendances) — version requise définie dans `pyproject.toml`.
- iputils `ping` disponible dans le PATH (utilisé en sous‑processus).
- Accès réseau sortant selon vos cibles.

[⬆️ Retour en haut](#ip-monitor)

## Installation (UV)
- Installer les dépendances: `uv sync`
- Optionnel (développement): `uv sync --all-groups` ou `uv sync --group dev`

[⬆️ Retour en haut](#ip-monitor)

## Utilisation (CLI)
- Lancer: `uv run ip-monitor -c config.yaml`
- Options principales:
  - `-c/--config`: chemin du fichier YAML (par défaut intégré à l’appli)
  - `-l/--log-level`: `DEBUG|INFO|WARNING|ERROR|CRITICAL` (défaut: WARNING)
  - `--precheck-enabled` / `--no-precheck`: active/désactive la pré‑vérification Internet (défaut activée)
  - `--precheck-timeout`: timeout (s) du ping de pré‑vérification (défaut YAML ou 10.0)
  - `--ping-timeout`: timeout (s) d’un ping IP (défaut YAML ou 15.0)
  - `--http-timeout`: timeout total (s) des requêtes HTTP (défaut YAML ou 7.0)
  - `--http-connector-limit`: connexions HTTP max (défaut YAML ou 50)
  - `--concurrency`: vérifications concurrentes max (défaut YAML ou 20)
  - `--quiet` / `--no-quiet`: désactive/force les messages de progression (par défaut: affichés). Peut aussi être contrôlé par `IPM_QUIET=1`.

[⬆️ Retour en haut](#ip-monitor)

## Configuration YAML complète
Placez un fichier `config.yaml`, par exemple:

```yaml
db_path: /var/lib/ip-monitor/ipmonitor.db
notify_method: ntfy  # ntfy | smsbox

# ntfy.sh (obligatoire si notify_method=ntfy)
ntfy:
  server: http://ntfy.example.local
  topic: monitoring

# smsbox.net (obligatoire si notify_method=smsbox)
# smsbox:
#   api_key: "votre_clef_api"
#   recipient: "+33601020304"

# Cibles surveillées (au moins une entrée parmi ips ou urls)
ips:
  - ip: 1.2.3.4
    description: routeur
urls:
  - url: example.org
    description: site

# Paramètres optionnels (valeurs par défaut entre parenthèses)
precheck_enabled: true      # active la pré‑vérification Internet (true)
precheck_timeout: 10.0      # s (10.0)
ping_timeout: 15.0          # s (15.0)
http_timeout: 7.0           # s (7.0)
http_connector_limit: 50    # connexions HTTP max (50)
concurrency: 20             # tâches concurrentes max (20)
```

Fichier d’exemple: `config.example.yaml` est fourni dans le dépôt. Copiez‑le et adaptez‑le:
- Local: `cp config.example.yaml config.yaml`
- Système: `sudo install -D -m 640 config.example.yaml /etc/ip-monitor/config.yaml`

Emplacements par défaut (platformdirs):
- Config par défaut (ordre de recherche):
  1. `IPM_CONFIG` (si défini)
  2. `./config.yaml`
  3. `${XDG_CONFIG_HOME:-~/.config}/ip-monitor/config.yaml`
  4. `${XDG_CONFIG_DIRS}/ip-monitor/config.yaml` via `site_config_dir` (ex: `/etc/xdg/ip-monitor/config.yaml`)
  5. Linux: `/etc/ip-monitor/config.yaml`
- Base de données par défaut: `${XDG_DATA_HOME:-~/.local/share}/ip-monitor/ipmonitor.db`
  - Le dossier de données est créé automatiquement si nécessaire.

[⬆️ Retour en haut](#ip-monitor)

## Détails de schéma et validations
- `db_path` (Path): dossier parent existant + permission d’écriture requise.
- `notify_method` (enum): `ntfy` ou `smsbox`.
- `ntfy` (si `notify_method=ntfy`):
  - `server` (URL): ex. `http://ntfy.example.local`
  - `topic` (str): sujet de publication
- `smsbox` (si `notify_method=smsbox`):
  - `api_key` (str): clé API
  - `recipient` (str): numéro destinataire
- `ips` (liste): éléments `{ip: str, description: str}`
- `urls` (liste): éléments `{url: str, description: str}` (schéma minimal)
- Au moins une entrée dans `ips` ou `urls` est requise.
- Paramètres de performance: tous strictement > 0.

[⬆️ Retour en haut](#ip-monitor)

## Overrides via ENV et CLI (priorité)
- Ordre de priorité: CLI > variables d’environnement > YAML > valeurs par défaut.
- Variables d’environnement supportées:
  - `IPM_PRECHECK_ENABLED` (0/1, true/false, yes/no, on/off)
  - `IPM_PRECHECK_TIMEOUT`
  - `IPM_PING_TIMEOUT`
  - `IPM_HTTP_TIMEOUT`
  - `IPM_HTTP_CONNECTOR_LIMIT`
  - `IPM_CONCURRENCY`
- Exemples:
  - ENV: `IPM_CONCURRENCY=10 IPM_HTTP_TIMEOUT=5 uv run ip-monitor -c config.yaml`
  - CLI: `uv run ip-monitor -c config.yaml --concurrency 10 --http-timeout 5`

[⬆️ Retour en haut](#ip-monitor)

## Fonctionnement interne
- Pré‑vérification Internet: ping `1.1.1.1` (optionnelle). Si échec, arrêt sans ouvrir la BDD.
- Ping IP: exécute `ping -q -s26 -c5 <ip>` en sous‑processus. On force la locale (`LC_ALL=C`) et on se base sur le code retour (`0` = au moins une réponse). Chaque ping est borné par `asyncio.wait_for`.
- Vérification URL: `HEAD` puis `GET` si nécessaire (HTTP 200 attendu). Timeout global via `aiohttp.ClientTimeout(total=...)`.
- Concurrence: limitée par sémaphore (`--concurrency`). Les tâches sont agrégées avec `asyncio.gather(..., return_exceptions=True)` et les exceptions sont journalisées sans stopper l’ensemble.
- Persistance SQLite: table `status(type TEXT, address TEXT, down INTEGER)`, unique `(type,address)`. Nettoyage des entrées obsolètes avant chaque cycle.

[⬆️ Retour en haut](#ip-monitor)

## Déploiement (systemd)

Le binaire effectue une seule passe puis s’arrête. L’intégration recommandée sous systemd est donc: un service `oneshot` déclenché par un `timer`.

Des unités prêtes à l’emploi sont fournies dans `contrib/systemd/`.

### Unités

`contrib/systemd/ip-monitor.service` (oneshot):

```ini
[Unit]
Description=IP Monitor (oneshot)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/ip-monitor
ExecStart=/usr/bin/env uv run ip-monitor -c /etc/ip-monitor/config.yaml -l INFO
User=ipmonitor
Group=ipmonitor
Environment=IPM_CONCURRENCY=20
# Rendez le service silencieux si souhaité (prints désactivés)
Environment=IPM_QUIET=1
## Alternative: pointer explicitement vers un fichier de config
# Environment=IPM_CONFIG=/etc/ip-monitor/config.yaml
```

`contrib/systemd/ip-monitor.timer`:

```ini
[Unit]
Description=Planification périodique d'IP Monitor

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
AccuracySec=30s
Persistent=true
Unit=ip-monitor.service

[Install]
WantedBy=timers.target
```

### Installation

1) Copier les unités dans `/etc/systemd/system/`:

```bash
sudo install -m 644 contrib/systemd/ip-monitor.service /etc/systemd/system/
sudo install -m 644 contrib/systemd/ip-monitor.timer   /etc/systemd/system/
```

2) Recharger et activer le timer (ne pas activer le service) :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ip-monitor.timer
```

3) Vérifier:

```bash
systemctl status ip-monitor.timer
systemctl list-timers ip-monitor*
systemctl status ip-monitor.service   # dernier run
```

Remarques:
- Le service ne boucle pas: il s’exécute une fois à chaque déclenchement du timer.
- Ajustez la périodicité via `OnUnitActiveSec=` et la tolérance via `AccuracySec=`.
- Les paramètres d’exécution peuvent être surchargés via `Environment=` ou des drop‑ins (`systemctl edit ip-monitor.service`).

[⬆️ Retour en haut](#ip-monitor)

## Déploiement serveur
- Emplacement recommandé de la configuration système: `/etc/ip-monitor/config.yaml`.
- Installation rapide (droits lecture groupe seulement):
  - `sudo install -d -m 755 /etc/ip-monitor`
  - `sudo install -m 640 config.example.yaml /etc/ip-monitor/config.yaml`
  - Optionnel: `sudo chown root:ipmonitor /etc/ip-monitor/config.yaml`
- Découverte automatique: ip-monitor cherchera aussi dans `/etc/ip-monitor/config.yaml` par défaut; l’option `-c` est donc facultative sur un serveur.
- Overrides et ordre de recherche:
  - Vous pouvez forcer le chemin via `IPM_CONFIG=/chemin/config.yaml` ou l’option `-c`.
  - Ordre de recherche sans override: `./config.yaml` → `${user_config_dir}/ip-monitor/config.yaml` → `${site_config_dir}/ip-monitor/config.yaml` (ex: `/etc/xdg/ip-monitor/config.yaml`) → `/etc/ip-monitor/config.yaml`.
- Base de données: par défaut dans le répertoire de données utilisateur du service (ex: `/var/lib/<user>/.local/share/ip-monitor/ipmonitor.db`).
  - Recommandé: définir explicitement `db_path: /var/lib/ip-monitor/ipmonitor.db` dans le YAML et créer le dossier avec les droits adéquats:
    - `sudo install -d -m 750 -o ipmonitor -g ipmonitor /var/lib/ip-monitor`

## Développement
- Tests unitaires: `uv run pytest -q`
- Lint (ruff): `uv run ruff check .`
- Types (mypy): `uv run mypy`
- Formatage: suivez la config ruff (E501 ignoré, longueur 80 dans config ruff).

[⬆️ Retour en haut](#ip-monitor)

## Couverture de tests
- Mesure: activée via pytest-cov, configurée dans `pyproject.toml`.
- Commandes utiles:
  - Rapide: `uv run pytest`
  - Terminal détaillé: `uv run pytest -q`
  - Rapport HTML: généré dans `htmlcov/index.html`
  - Rapport XML: `coverage.xml` (CI/outils externes)
- Seuil en échec: 95% (modifiable via `--cov-fail-under` ou `tool.coverage.report.fail_under`).
- Cible: viser ~100%; ajuster au besoin et compléter les tests.

[⬆️ Retour en haut](#ip-monitor)

## Dépannage (FAQ)
- « Pas de connexion à Internet. » au démarrage:
  - L’ICMP peut être filtré. Désactivez la pré‑vérif (`precheck_enabled: false` ou `--no-precheck`) ou augmentez `precheck_timeout`.
- IP marquée down trop vite:
  - Augmentez `ping_timeout`. Vérifiez aussi la latence réseau ou la charge.
- Verrouillage ou sortie tardive:
  - Les connexions SQLite sont désormais fermées proprement même en cas d’erreur.
- Permissions BDD:
  - Assurez‑vous que le dossier parent de `db_path` existe et est accessible en écriture par l’utilisateur d’exécution.
- `ping` introuvable:
  - Installez iputils (`ping` dans le PATH du service). Le script force `LC_ALL=C`, la sortie n’est pas parsée (code retour utilisé).

[⬆️ Retour en haut](#ip-monitor)

## Licence
- MIT (cf. `pyproject.toml`).

[⬆️ Retour en haut](#ip-monitor)

## Feuille de route (TODO)
- Timer et service systemd: fournir unités `*.service` et `*.timer`, avec exemple d’installation et d’override via Environment.
- Packaging Debian: ajouter un dossier `debian/` (control, rules, install), dépendances, intégration systemd (dh_systemd), scripts postinst/prerm si nécessaire.
- Manpage: rédiger une page man pour `ip-monitor` (section 1), utile pour l’intégration Debian et l’aide locale.
- Couverture de tests: ajouter la mesure de coverage (objectif ~100%), configurer précisément pytest et coverage dans `pyproject.toml` (inclure/exclure, branch coverage, seuils), et envisager un réglage plus strict de mypy si pertinent.

[⬆️ Retour en haut](#ip-monitor)
