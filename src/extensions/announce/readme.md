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
  renseignée. Cette règle vaut côté Discord ; l'API fait confiance au Dashboard (voir plus bas).
- **Salon cible explicite** : contrairement à l'ancien comportement (postait dans le salon où la
  commande était tapée), un salon doit être choisi explicitement — nécessaire dès lors que l'envoi
  peut avoir lieu des jours plus tard, ou être déclenché depuis le Dashboard (pas de "salon
  courant" possible dans ce cas).
- **Image stockée sur S3** : l'image uploadée est gardée dans le stockage objet configuré par
  `db.s3` (champ `S3Field` de `tortoise_extensions`), la base ne contient que sa clé. PNG, JPEG,
  GIF ou WebP uniquement, 10 Mio au plus (la limite d'envoi de Discord pour un serveur sans
  boost). Le nom du fichier est nettoyé avant d'être utilisé dans `attachment://`.
- **Longueur** : Discord refuse un message dont le texte (mentions, titre, contenu, pied de page
  et signature réunis) dépasse 4000 caractères. Le panneau l'affiche et bloque l'envoi, l'API
  répond 422.
- **Programmation** : une boucle vérifie chaque minute les annonces `SCHEDULED` dont l'heure est
  passée et les envoie en parallèle (`AnnounceSchedulerCog`, même technique que la boucle de
  `stats_staff`). Un envoi qui échoue (salon supprimé, permission manquante, image introuvable)
  passe en `FAILED` plutôt que d'être retenté indéfiniment, sans bloquer les autres.
- **Verrouillage** : envoyer, modifier et annuler ne s'appliquent qu'à une annonce encore
  `SCHEDULED`, via un `UPDATE` conditionnel. Un envoi fait d'abord passer l'annonce en `SENDING`,
  si bien qu'une seule des actions concurrentes (boucle, "Envoyer maintenant", modification,
  annulation) l'emporte et les autres voient qu'elle n'est plus programmée. Une annonce restée
  `SENDING` après un arrêt du bot passe en `FAILED` au démarrage, plutôt que d'être renvoyée au
  risque d'un doublon.
- **Historique** : `/announce historique` liste les annonces récentes (programmées, en cours
  d'envoi, envoyées, annulées, échouées) avec, par entrée, "Dupliquer" (réouvre le panneau
  prérempli, image comprise, jamais avec l'ancienne date, toujours comme un nouveau brouillon) et,
  pour les `SCHEDULED`, "Modifier", "Annuler" et (admins) "Envoyer maintenant".
- **Modification avant envoi** : "Modifier" (ou l'équivalent côté Dashboard) ouvre le même panneau
  que la création, prérempli avec les valeurs actuelles de l'annonce, et modifie la ligne en base
  en place (contrairement à "Dupliquer", qui en crée une nouvelle). La date/heure reste toujours
  obligatoire ici, même pour un admin — une annonce déjà `SCHEDULED` ne doit jamais repasser en
  "envoi instantané" via une édition. Seule une annonce encore `SCHEDULED` peut être modifiée (409
  sinon, même règle que l'annulation) ; une fois envoyée, elle ne l'est plus depuis ce module (le
  message Discord peut toujours être édité/supprimé manuellement).
- **Traductions** : tous les textes, y compris la signature "Annonce effectuée par", viennent de
  `translations.yml`. Le panneau suit la langue du membre, le message envoyé celle du serveur.

## Commandes

- `/announce creer` : composer et envoyer/programmer une annonce.
- `/announce historique` : consulter, annuler ou dupliquer les annonces récentes.
- `/announce-admin config` : configurer les rôles (en plus des admins) autorisés à programmer.

## API (panel admin)

Routes HTTP sous `/announce/v1`, toutes protégées par la clé API de l'extension `dashboard_api`
(voir son readme). Toutes prennent un `guild_id` dans le chemin.

Le Dashboard est considéré fiable : les identifiants qu'il envoie (salon, rôles, auteur) et les
permissions de l'utilisateur derrière lui ne sont pas revérifiés. Seul ce que Discord ou ce module
refuserait est contrôlé, avec une erreur explicite :

- **422** : champ trop long, plus de 10 rôles à mentionner, texte rendu de plus de 4000
  caractères, `scheduled_for` passée, image d'un type non accepté ou de plus de 10 Mio. Le
  `detail` suit le format de validation de FastAPI (`loc`, `msg`, `type`).
- **409** : l'annonce n'est plus `SCHEDULED` ; le message donne son statut actuel.
- **404** : l'annonce n'existe pas dans cette guilde.

Routes :

- `GET /guilds/{guild_id}/announcements` : liste des annonces récentes (ne renvoie pas l'image
  elle-même, juste `has_image` — voir la route dédiée ci-dessous).
- `POST /guilds/{guild_id}/announcements` : crée une annonce. En `multipart/form-data` (pas un
  corps JSON) puisqu'un upload d'image peut l'accompagner. `scheduled_for` absent = envoi
  immédiat tout de suite après création ; une valeur future = programmée (reprise par la boucle
  planifiée) ; une valeur passée est refusée (422).
- `PUT /guilds/{guild_id}/announcements/{id}` : modifie une annonce encore `SCHEDULED` en place.
  Même format `multipart/form-data` que la création ; `scheduled_for` est ici obligatoire (une
  édition ne peut jamais transformer une annonce programmée en envoi instantané).
  `clear_image=true` retire l'image existante sans la remplacer ; un nouveau fichier `image` la
  remplace ; absent des deux, l'image actuelle est conservée telle quelle.
- `GET /guilds/{guild_id}/announcements/{id}/image` : l'image stockée, avec le type MIME déduit de
  son nom.
- `DELETE /guilds/{guild_id}/announcements/{id}` : annule une annonce encore `SCHEDULED`.
- `POST /guilds/{guild_id}/announcements/{id}/send-now` : force l'envoi immédiat d'une annonce
  encore `SCHEDULED`.
- `GET /guilds/{guild_id}/settings` / `PUT /guilds/{guild_id}/settings` : lit/écrit
  `allowed_role_ids` — mêmes réglages que `/announce-admin config`. L'écriture plafonne la liste à
  25 (limite d'un menu déroulant Discord) et retire les doublons.
