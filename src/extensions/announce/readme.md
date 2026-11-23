<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz -->

# announce

Crée et programme des annonces Discord riches (titre, contenu, pied de page, image, rôles à
mentionner), depuis Discord ou le Dashboard externe. Toute annonce (instantanée ou programmée) est
journalisée pour garder un historique consultable et dupliquable.

## Ce que fait le module

- **Composition** : `/announce creer` ouvre un panneau éphémère (pas une simple modale — trop de
  champs pour une seule modale Discord) avec aperçu en direct. "Modifier le contenu" (titre,
  contenu, pied de page, image), un sélecteur de salon cible et un sélecteur de rôles à mentionner
  sont toujours visibles ; "Modifier la programmation" ouvre une petite modale date/heure.
  "Aperçu" affiche le rendu final (éphémère) avant tout envoi réel.
- **Instantané vs programmé** : les **admins** peuvent envoyer tout de suite (date/heure laissées
  vides) ou programmer. **Le reste du staff** (rôles configurables via `/announce-admin config`,
  même mécanique que `allowed_role_ids` côté `absence`) peut **uniquement programmer** — la
  date/heure devient obligatoire, le bouton d'envoi reste désactivé tant qu'elle n'est pas
  renseignée. Aucun raccourci n'existe pour contourner cette règle : elle est revérifiée aussi
  bien côté modale que côté route API.
- **Salon cible explicite** : contrairement à l'ancien comportement (postait dans le salon où la
  commande était tapée), un salon doit être choisi explicitement — nécessaire dès lors que l'envoi
  peut avoir lieu des jours plus tard, ou être déclenché depuis le Dashboard (pas de "salon
  courant" possible dans ce cas).
- **Image stockée en base** : ce bot n'a aucun stockage de fichiers persistant (pas de volume
  monté, pas de stockage objet) — l'image uploadée est donc gardée en `bytea` Postgres jusqu'à
  l'envoi, cohérent avec le fait que la base est la seule persistance utilisée partout ailleurs
  dans ce bot.
- **Programmation** : une boucle vérifie chaque minute les annonces `SCHEDULED` dont l'heure est
  passée et les envoie (`AnnounceSchedulerCog`, même technique que la boucle de `stats_staff`). Un
  envoi qui échoue (salon supprimé, permission manquante) passe en `FAILED` plutôt que d'être
  retenté indéfiniment.
- **Historique** : `/announce historique` liste les annonces récentes (programmées, envoyées,
  annulées, échouées) avec, par entrée, "Dupliquer" (réouvre le panneau prérempli — jamais avec
  l'ancienne date, toujours comme un nouveau brouillon) et, pour les `SCHEDULED`, "Annuler" et
  (admins) "Envoyer maintenant".
- **Rien d'automatique au-delà de l'envoi** : une fois envoyée, une annonce n'est plus modifiable
  depuis ce module (le message Discord peut toujours être édité/supprimé manuellement).

## Commandes

- `/announce creer` : composer et envoyer/programmer une annonce.
- `/announce historique` : consulter, annuler ou dupliquer les annonces récentes.
- `/announce-admin config` : configurer les rôles (en plus des admins) autorisés à programmer.

## API (panel admin)

Routes HTTP sous `/announce/v1`, protégées par la clé API de l'extension `dashboard_api` (voir son
readme). Toutes prennent un `guild_id` dans le chemin :

- `GET /guilds/{guild_id}/announcements` : liste des annonces récentes (ne renvoie pas l'image
  elle-même, juste `has_image` — voir la route dédiée ci-dessous).
- `POST /guilds/{guild_id}/announcements` : crée une annonce. En `multipart/form-data` (pas un
  corps JSON) puisqu'un upload d'image peut l'accompagner. `scheduled_for` absent ou passé =
  envoi immédiat tout de suite après création ; une valeur future = programmée (reprise par la
  boucle planifiée).
- `GET /guilds/{guild_id}/announcements/{id}/image` : l'image stockée, en binaire brut.
- `DELETE /guilds/{guild_id}/announcements/{id}` : annule une annonce encore `SCHEDULED` (409
  sinon — une annonce déjà envoyée/annulée/échouée ne peut pas être ré-annulée).
- `POST /guilds/{guild_id}/announcements/{id}/send-now` : force l'envoi immédiat d'une annonce
  encore `SCHEDULED`.
- `GET /guilds/{guild_id}/settings` / `PUT /guilds/{guild_id}/settings` : lit/écrit
  `allowed_role_ids` — mêmes réglages que `/announce-admin config`. L'écriture valide que les
  rôles appartiennent bien à la guilde, et plafonne la liste à 25 (limite d'un menu déroulant
  Discord).
