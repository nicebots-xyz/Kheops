<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz -->

# dashboard_api

Socle d'authentification partagé pour les routes HTTP du panel admin. Ne contient aucune donnée
métier : chaque extension qui veut exposer des données au site (ex. `stats_staff`) monte ses
propres routes via son `setup_webserver`, en les protégeant avec la dépendance FastAPI fournie ici.

## Authentification

Toutes les routes exposées par n'importe quelle extension du panel admin doivent dépendre de
`require_api_key` (`src.extensions.dashboard_api.auth.require_api_key`) :

```python
from fastapi import APIRouter, Depends
from src.extensions.dashboard_api.auth import require_api_key

router = APIRouter(prefix="/mon_extension/v1", dependencies=[Depends(require_api_key)])
```

Le site appelle l'API avec un header `Authorization: Bearer <clé>`. Seul le **hash SHA-256** de la
clé est stocké côté bot, jamais la clé elle-même. La clé est générée en dehors de ce dépôt (côté
hébergeur du bot) ; stocker plusieurs hash permet une rotation sans interruption de service (on
ajoute le nouveau hash, puis on retire l'ancien une fois le site basculé).

## Configuration

```yaml
extensions:
  dashboard_api:
    enabled: true
    api_key_hashes:
      - "<sha256 hex de la clé en prod>"
```

Fonctionne aussi via variable d'environnement (`BOTKIT__EXTENSIONS__DASHBOARD_API__API_KEY_HASHES`,
JSON array) ou secret Docker (`BOTKIT_FILE__EXTENSIONS__DASHBOARD_API__API_KEY_HASHES`, fichier
contenant soit un JSON array, soit un seul hash brut — les deux formats sont acceptés).

## Routes

- `GET /dashboard_api/v1/health` — vérifie que la clé API configurée est valide, sans toucher à
  aucune donnée. Utile pour tester la connexion avant de brancher le site sur de vraies routes.

Pas de CORS ajouté : l'API n'est appelée que serveur à serveur par le back-end du site, jamais
directement depuis un navigateur.
