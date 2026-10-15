<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz -->

# absence

Permet aux membres du staff de déclarer leurs absences proprement, avec une annonce publique
(nom + dates, jamais la raison) et une gestion complète depuis Discord ou le Dashboard externe.

## Ce que fait le module

- **Déclaration** : `/absence declare` ouvre une modale (dates au format `JJ/MM/AAAA`, date de fin
  incluse, raison privée obligatoire). Un membre peut déclarer sa propre absence s'il a l'un des
  rôles autorisés (configurés par un admin) ; un admin peut déclarer une absence pour n'importe
  qui.
- **Validations** : la date de début d'une *nouvelle* déclaration ne peut pas être dans le passé
  (pas d'antidatage) ; une absence ne peut pas chevaucher une autre absence active du même membre.
  Ces deux règles ne s'appliquent qu'à la création — modifier une absence déjà en cours/passée
  reste possible.
- **Annonce publique** : si un salon d'annonce est configuré, une carte Discord est postée (nom,
  dates au format natif Discord, durée en jours) — jamais la raison. Mise à jour en cas de
  modification des dates, supprimée en cas d'annulation ou de suppression définitive.
- **Raison privée** : visible uniquement par les admins et par le membre concerné, jamais affichée
  publiquement.
- **`/absence mine`** : liste groupée en trois sections (en cours/à venir, passées, annulées), les
  plus proches en premier pour les à venir, les plus récentes en premier pour l'historique. Seules
  les absences en cours/à venir sont modifiables/annulables ; l'historique est limité aux entrées
  les plus récentes pour rester lisible après des mois d'usage (indicateur si des entrées plus
  anciennes sont masquées).
- **Annulation vs suppression définitive** : "Annuler" (tout le monde, sur ses propres absences
  en cours/à venir) est réversible et garde l'historique (`cancelled_at`). "Supprimer
  définitivement" efface la ligne en base — réservé au rôle **Responsable staff** configuré
  (délibérément pas accordé aux admins automatiquement, contrairement au reste du module).
- **Rien d'automatique** au passage de la date de fin : le statut (à venir / en cours / passée /
  annulée) est calculé à la volée, jamais stocké.
- **Pas de lien avec `stats_staff`** : les quotas d'activité ne sont pas affectés par une absence.

## Commandes

- `/absence declare [membre]` : déclarer une absence (pour soi, ou pour `membre` si admin).
- `/absence mine` : voir et gérer ses propres absences (modifier/annuler).
- `/absence-admin list <membre>` : voir et gérer les absences d'un membre (admin).
- `/absence-admin config` : configurer les rôles autorisés à se déclarer, le salon d'annonce, et le
  rôle responsable (suppression définitive).

## API (panel admin)

Routes HTTP sous `/absence/v1`, protégées par la clé API de l'extension `dashboard_api` (voir son
readme). Toutes prennent un `guild_id` dans le chemin. Chaque écriture met aussi à jour le message
d'annonce Discord correspondant, pour que le Dashboard et Discord restent toujours synchronisés :

- `GET /guilds/{guild_id}/absences?member_id=...` : liste des absences (reason incluse).
- `POST /guilds/{guild_id}/absences` : crée une absence (mêmes validations que la modale Discord).
- `PUT /guilds/{guild_id}/absences/{id}` : modifie une absence (dates, raison).
- `DELETE /guilds/{guild_id}/absences/{id}` : annule une absence (soft-delete, garde l'historique).
- `DELETE /guilds/{guild_id}/absences/{id}/permanent` : supprime définitivement une absence.
- `GET /guilds/{guild_id}/settings` / `PUT /guilds/{guild_id}/settings` : lit/écrit les rôles
  autorisés, le salon d'annonce et le rôle responsable — les mêmes réglages que
  `/absence-admin config`.
