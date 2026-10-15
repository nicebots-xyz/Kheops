<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz -->

# absence

Permet aux membres du staff de déclarer leurs absences proprement, avec une annonce publique
(nom + dates, jamais la raison) et une gestion complète depuis Discord ou le Dashboard externe.

## Ce que fait le module

- **Déclaration** : `/absence declare` ouvre une modale (dates au format `JJ/MM/AAAA`, raison
  privée). Un membre peut déclarer sa propre absence s'il a l'un des rôles autorisés (configurés
  par un admin) ; un admin peut déclarer une absence pour n'importe qui.
- **Annonce publique** : si un salon d'annonce est configuré, un message est posté
  (`<@membre> absent du JJ/MM/AAAA au JJ/MM/AAAA`) — jamais la raison. Le message est mis à jour en
  cas de modification des dates, et supprimé en cas d'annulation.
- **Raison privée** : visible uniquement par les admins et par le membre concerné, jamais affichée
  publiquement.
- **Historique illimité** : un membre peut avoir plusieurs absences passées, en cours ou à venir ;
  une absence annulée est gardée en base (marquée `cancelled_at`), jamais supprimée.
- **Rien d'automatique** au passage de la date de fin : le statut (à venir / en cours / passée /
  annulée) est calculé à la volée, jamais stocké.
- **Pas de lien avec `stats_staff`** : les quotas d'activité ne sont pas affectés par une absence.

## Commandes

- `/absence declare [membre]` : déclarer une absence (pour soi, ou pour `membre` si admin).
- `/absence mine` : voir et gérer ses propres absences (modifier/annuler).
- `/absence-admin list <membre>` : voir et gérer les absences d'un membre (admin).
- `/absence-admin config` : configurer les rôles autorisés à se déclarer et le salon d'annonce.

## API (panel admin)

Routes HTTP sous `/absence/v1`, protégées par la clé API de l'extension `dashboard_api` (voir son
readme). Toutes prennent un `guild_id` dans le chemin. Chaque écriture met aussi à jour le message
d'annonce Discord correspondant, pour que le Dashboard et Discord restent toujours synchronisés :

- `GET /guilds/{guild_id}/absences?member_id=...` : liste des absences (reason incluse).
- `POST /guilds/{guild_id}/absences` : crée une absence.
- `PUT /guilds/{guild_id}/absences/{id}` : modifie une absence (dates, raison).
- `DELETE /guilds/{guild_id}/absences/{id}` : annule une absence (soft-delete, garde l'historique).
- `GET /guilds/{guild_id}/settings` / `PUT /guilds/{guild_id}/settings` : lit/écrit les rôles
  autorisés et le salon d'annonce — les mêmes réglages que `/absence-admin config`.
