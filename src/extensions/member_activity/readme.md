<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz -->

# member_activity

Activité brute (messages, temps vocal) de **tous** les membres du serveur — par opposition à
`stats_staff`, qui ne suit que les membres ayant un rôle avec un quota configuré, et qui mélange
cette donnée à une notion de conformité/quota. Ici : pas de quota, pas de rapport hebdomadaire,
pas de notion de "staff" — juste des compteurs descriptifs, ouverts à tout le monde.

## Ce que fait le module

- **Messages** : comptés uniquement dans les « salons suivis (messages) », ou dans tout salon
  appartenant à une « catégorie suivie ».
- **Vocal** : compté uniquement dans les « salons suivis (vocal) » ou tout salon vocal d'une
  « catégorie suivie », tant que le membre n'est ni muet ni sourd (lui-même ou par le serveur) et
  qu'au moins une autre personne (non-bot) est dans le salon — même règle anti-AFK que
  `stats_staff` (voir son readme pour le détail), gardée identique exprès pour que "temps vocal"
  veuille dire la même chose dans les deux extensions.
- **Qui est suivi** : tout membre humain (les bots ne comptent jamais), sans condition de rôle —
  contrairement à `stats_staff` qui ne suit que les membres à quota.
- Aucun rapport automatique, aucune notion de conformité : juste des totaux et un historique
  jour par jour, consultables via commande ou l'API du panel admin.

## Commandes

Noms par défaut en anglais, traduits en français via `translations.yml` (`/mon-activite`,
`/voir`, section `strings` pour le reste des textes).

- `/member-activity me [period]` (`mon-activite`) : mon activité, ouvert à tout le monde.
- `/member-activity view <member> [period]` (`voir`) : activité d'un autre membre, ouvert à tout
  le monde (pas de restriction, contrairement à `stats_staff view` réservé aux admins/responsable).
- `/member-activity-admin config` : salons/catégories suivis. Réservé aux administrateurs du
  serveur par défaut (`default_member_permissions`), délégable via les permissions de commandes
  Discord — même mécanisme que `stats-staff-admin`.

## API (panel admin)

Routes HTTP sous `/member_activity/v1`, protégées par la clé API de l'extension `dashboard_api`
(voir son readme). Jamais appelées par un navigateur, seulement par le back-end du site.

- `GET /guilds/{guild_id}/members/{member_id}/stats?period=week|month|last_3_months|last_6_months|all_time` :
  totaux messages/vocal sur la période.
- `GET /guilds/{guild_id}/members/{member_id}/history?start=YYYY-MM-DD&end=YYYY-MM-DD` : messages
  et minutes de vocal jour par jour (jours Europe/Paris), 366 jours maximum par requête.
- `GET /guilds/{guild_id}/config` / `PUT /guilds/{guild_id}/config` : salons/catégories suivis.

Les lectures font un flush avant de répondre (données à jour à la seconde près), et les écritures
de config préviennent le suivi tout de suite.

## Architecture de tracking

Même moteur de sessions que `stats_staff` (`VoiceTracker`, flush toutes les 2 minutes, une ligne
par session plutôt qu'une ligne par minute) — voir le readme de `stats_staff` pour le détail
complet (pourquoi des sessions, pourquoi pas de verrou hors du flush, ce que coûte un crash). La
seule différence : pas de filtre par rôle à quota dans `counting_channel_id`/`on_message`, tout
membre humain compte.

Tables dédiées (`MemberActivityMessageEvent`, `MemberActivityVoiceSession`,
`MemberActivitySettings`), volontairement séparées de celles de `stats_staff` pour ne jamais
mélanger les deux notions, même si la structure est quasi identique.
