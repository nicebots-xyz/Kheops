<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz -->

# absence

Permet aux membres du staff de déclarer leurs absences proprement, avec une annonce publique
(nom + dates, jamais la raison) et une gestion complète depuis Discord ou le Dashboard externe.

## Ce que fait le module

- **Déclaration** : `/absence declare` ouvre une modale (dates au format `JJ/MM/AAAA`, date de fin
  incluse, raison privée obligatoire, type, note de disponibilité). Un membre peut déclarer sa
  propre absence s'il a l'un des rôles autorisés (configurés par un admin) ; un admin peut
  déclarer une absence pour n'importe qui.
- **Type d'absence** : `Absence totale` (indisponible, comportement historique) ou
  `Disponibilité réduite` (joignable mais plus difficilement — ex. cours, événements récurrents).
  La note de disponibilité (ex. "dispo le soir après 19h", "pas mardi/jeudi") n'est affichée
  publiquement que pour une absence de type "Disponibilité réduite" — elle est ignorée (mise à
  `null`) pour une absence totale, même si le champ a été rempli dans la modale.
- **Validations** : la date de début d'une *nouvelle* déclaration ne peut pas être dans le passé
  (pas d'antidatage) ; une absence ne peut pas chevaucher une autre absence active du même membre.
  Ces deux règles ne s'appliquent qu'à la création — modifier une absence déjà en cours/passée
  reste possible.
- **Annonce publique** : si un salon d'annonce est configuré, une carte Discord est postée (nom,
  dates au format `JJ/MM/AAAA`, durée en jours, et la note de disponibilité si le type est
  "Disponibilité réduite") — jamais la raison privée. Couleur/titre distincts selon le type
  (🔴 rouge pour une absence totale, 🟠 orange pour une disponibilité réduite). Dates en texte
  simple plutôt qu'au format natif Discord (`<t:...>`) pour éviter un décalage d'un jour selon le
  fuseau horaire du lecteur. Mise à jour en cas de modification des dates/type/note, supprimée en
  cas d'annulation ou de suppression définitive.
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

- `GET /guilds/{guild_id}/absences?member_id=...` : liste des absences (reason, kind et
  availability_note inclus).
- `POST /guilds/{guild_id}/absences` : crée une absence (mêmes validations que la modale Discord ;
  409 en cas de chevauchement, protégé contre les écritures concurrentes par un verrou transactionnel
  par membre). Accepte `kind` (`full` par défaut, ou `partial`) et `availability_note` (ignorée côté
  serveur si `kind` n'est pas `partial`).
- `PUT /guilds/{guild_id}/absences/{id}` : modifie une absence (dates, raison, kind,
  availability_note) ; 409 si l'absence a été annulée entre-temps.
- `DELETE /guilds/{guild_id}/absences/{id}` : annule une absence (soft-delete, garde l'historique).
- `POST /guilds/{guild_id}/absences/{id}/restore` : annule une annulation (re-vérifie les
  chevauchements).
- `DELETE /guilds/{guild_id}/absences/{id}/permanent?actor_id=...` : supprime définitivement une
  absence. `actor_id` (l'utilisateur du Dashboard à l'origine de l'action) est obligatoire : ses
  rôles sont vérifiés côté bot pour confirmer qu'il a bien le rôle **Responsable staff** configuré —
  la clé API seule ne suffit pas, elle authentifie le backend du Dashboard, pas l'utilisateur final.
- `GET /guilds/{guild_id}/settings` / `PUT /guilds/{guild_id}/settings` : lit/écrit les rôles
  autorisés, le salon d'annonce et le rôle responsable — les mêmes réglages que
  `/absence-admin config`. L'écriture valide que le salon et les rôles appartiennent bien à la
  guilde, et plafonne `allowed_role_ids` à 25 (limite d'un menu déroulant Discord).
