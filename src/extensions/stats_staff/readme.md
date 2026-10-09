<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz -->

# stats_staff

Suivi des quotas d'activité hebdomadaires du staff : messages et temps vocal « valide ».

## Ce que fait le module

- **Messages** : comptés uniquement dans les salons choisis comme « salons suivis (messages) ».
- **Vocal** : compté uniquement dans les « salons suivis (vocal) », tant que le membre n'est ni muet ni
  sourd (lui-même ou par le serveur) et qu'au moins une autre personne (non-bot) est dans le salon.
- **Quotas par rôle** : un nombre d'heures de vocal et un nombre de messages par semaine, combinés en :
  - **OU** : les deux se cumulent. Sur « 4h OU 100 messages », 2h + 50 messages = 50 % + 50 % = quota atteint.
    Un critère à 0 ne compte pas.
  - **ET** : les deux sont requis, mais un manque d'un côté peut être compensé de l'autre avec une pénalité
    (125 % par défaut, réglable). Sur « 6h ET 100 messages », sauter les messages demande
    6h + 125 % de 6h = 13,5h de vocal. Si les deux critères sont en dessous du seuil, c'est un échec.
    Un critère à 0 est considéré comme atteint.
  - Un quota à 0 des deux côtés est toujours atteint.
  - La barre de progression affiche exactement le score qui décide du ✅/❌ (≥ 100 % = atteint).
- **Rapport hebdomadaire** : chaque lundi à 00:05 (Europe/Paris), pour la semaine qui vient de finir, dans le
  salon de rapport. Un message d'en-tête, puis un message par rôle. Les membres sans aucune activité sont
  marqués 🚨 et listés dans une alerte en tête du rapport.
  **Seul le rôle responsable est pingé** (ni les rôles du staff, ni les membres listés). Pour changer ça,
  voir le commentaire dans `report.py` (`send_report`).
  Si le bot est éteint pile à 00:05 un lundi, le rapport de cette semaine n'est pas envoyé ;
  `/stats-staff-admin preview-report` permet de le voir à tout moment.
- **Tendance** : en cours de semaine (`me`, `view`, aperçu), la semaine en cours est comparée à la semaine
  dernière *jusqu'au même jour et à la même heure*. Le rapport du lundi compare deux semaines complètes.
- **Qui apparaît dans le rapport** : les membres qui ont un rôle à quota au moment du rapport.
- **Membres avec plusieurs rôles à quota** : on applique le rôle assigné à la main (panel de config →
  quotas → « Assigner les membres à rôles multiples »), sinon leur rôle à quota le plus haut.

## Commandes

Noms par défaut en anglais, traduits en français via `translations.yml`.

- `/stats-staff me [period]` (`moi`) : mes stats, réservé aux membres ayant un rôle à quota.
- `/stats-staff view <member> [period]` (`voir`) : stats d'un membre, réservé aux admins et au rôle responsable.
- `/stats-staff-admin config` : panel de configuration (rôle responsable, salon de rapport, salons suivis,
  quotas, pénalité ET, assignations). Réservé aux admins ; délégable via les permissions de commandes du serveur.
- `/stats-staff-admin preview-report` (`apercu-rapport`) : aperçu du rapport de la semaine en cours.

Tous les textes affichés sont dans `translations.yml` (section `strings`).

## API (panel admin)

Routes HTTP sous `/stats_staff/v1`, protégées par la clé API de l'extension `dashboard_api` (voir son
readme). Elles ne sont jamais appelées par un navigateur, seulement par le back-end du site. Toutes prennent
un `guild_id` dans le chemin :

- `GET /guilds/{guild_id}/members/{member_id}/stats?period=week|month|last_3_months|last_6_months|all_time` :
  totaux messages/vocal sur la période.
- `GET /guilds/{guild_id}/members/{member_id}/history?start=YYYY-MM-DD&end=YYYY-MM-DD` : messages et minutes de
  vocal jour par jour (jours Europe/Paris), 366 jours maximum par requête, en une seule requête SQL.
- `GET /guilds/{guild_id}/quotas` : quotas par rôle.
- `PUT /guilds/{guild_id}/quotas/{role_id}` : crée ou met à jour le quota d'un rôle (404 si le rôle n'existe
  pas dans la guilde).
- `DELETE /guilds/{guild_id}/quotas/{role_id}` : supprime le quota d'un rôle.

Les lectures font un flush avant de répondre (données à jour à la seconde près), et les écritures de quotas
préviennent le suivi tout de suite. Aucune route ne reflète les permissions Discord : l'autorisation se fait
uniquement par la clé API, détenue par le back-end du site.

## Comment le vocal est compté

### L'idée : des « sessions »

Une **session** est un moment continu où un membre compte, **dans un seul salon**. Dès que quelque chose change,
la session se ferme ; si le membre compte encore, une nouvelle session commence :

```
vocal      ██████████████░███████████████████|███████████░░░░███████
             #salon-1     ↑muet 1s  #salon-1  ↑change  #salon-2  ↑seul
sessions   [─────────────][─────────────────][─────────]     [──────]
```

Ce qui ferme une session : se mettre muet ou sourd (même une seconde), rester seul, quitter, changer de salon,
perdre son rôle à quota, ou un salon qui n'est plus suivi. Une session de 2h50 contient donc toujours
2h50 de vocal valide, sans trou caché.

### Où vivent les sessions

Les sessions en cours sont gardées **en mémoire** (`VoiceTracker` dans `tracking.py`). Toutes les **2 minutes**,
un « flush » les écrit en base en une seule requête groupée :

- chaque session reçoit son identifiant (UUID) **dès son ouverture, en mémoire** ;
- à chaque flush, on écrit « la session X va de A jusqu'à maintenant » ; si la ligne existe déjà, on met
  juste à jour sa fin (`ON CONFLICT (id) DO UPDATE SET ended_at = ...`) ;
- une session longue reste donc **une seule ligne**, prolongée à chaque flush ;
- les messages sont aussi gardés en mémoire (avec leur heure exacte) et écrits par le même flush ;
- les écritures sont faites dans une transaction : si elle échoue, rien n'est perdu, tout est remis en
  mémoire et réessayé au flush suivant.

### Pourquoi il n'y a (presque) pas de verrou

asyncio ne passe d'une tâche à l'autre **que sur un `await`**. Toutes les fonctions qui modifient les sessions
(`VoiceTracker.sync`, `take`, `restore`) sont **synchrones** : elles s'exécutent d'un bloc, sans pouvoir être
interrompues au milieu. Aucun verrou n'est donc nécessaire autour des événements Discord.

Il y a **un seul verrou**, autour du flush : sans lui, deux flushs lancés en même temps (la boucle, et un `/stats`)
pourraient finir dans le désordre et faire reculer la fin d'une session.

### Pourquoi on regarde l'état actuel et pas `before`/`after`

py-cord met à jour son cache **avant** de lancer nos listeners, et l'objet `after` est l'objet du cache
lui-même (il continue d'évoluer). Quand notre code s'exécute, le cache peut donc déjà être plus récent que
l'événement. Plutôt que de comparer `before` et `after`, on se demande simplement :
« ce membre compte-t-il **maintenant**, et dans quel salon ? » (`counting_channel_id`). Si l'état a déjà
changé, on applique la vérité la plus récente quelques millisecondes en avance ; l'événement suivant
donnera la même réponse.

Un événement vocal re-vérifie le membre **et tous ceux des salons d'avant et d'après** (quelqu'un qui part peut
laisser un autre seul). On re-vérifie aussi :

- quand les rôles d'un membre changent (`on_member_update`) ;
- après chaque modification dans le panel de configuration ;
- à chaque flush, pour tous les membres des salons suivis : ça couvre le démarrage du bot et les événements
  manqués pendant une déconnexion.

Le module active l'intent **Members** (`__init__.py`) : sans lui, py-cord ne connaît pas les membres déjà en
vocal au démarrage, ni les membres des rôles pour le rapport.

### Ce que coûte un crash

Au pire les ~2 dernières minutes de vocal et de messages, depuis le dernier flush. On ne compte **jamais trop** :
une session coupée par un crash s'arrête au dernier flush, et une nouvelle commence au redémarrage.

### Limites connues

- Un muet/démuet pendant que le bot est déconnecté de Discord est invisible (Discord ne nous l'envoie pas).
- Un changement plus court que le temps de réaction du bot (quelques millisecondes, ou plus si la boucle
  asyncio est bloquée) peut être fusionné dans la session.
- Un changement de config ou de rôle fait hors des cas ci-dessus est pris en compte au flush suivant (≤ 2 min).

## Comment les stats sont calculées

Une seule fonction, `get_stats` (`stats.py`) : un `COUNT` des messages, et une requête SQL qui additionne, pour
chaque session, la partie qui tombe dans la période demandée :

```sql
SUM(EXTRACT(EPOCH FROM LEAST(ended_at, :fin) - GREATEST(started_at, :début)))
```

Une session à cheval sur minuit dimanche est donc coupée proprement entre les deux semaines. Avant de lire,
les commandes et le rapport font un flush pour inclure les dernières minutes.

## Pourquoi l'ancienne version a été remplacée

La première version de ce module (PR #116, avant refonte) comptait aussi le vocal par segments, mais autrement :
un segment était créé en base dès qu'un membre commençait à compter (avec une fin vide), puis **chaque minute**
chaque segment ouvert était fermé et un nouveau créé. Au démarrage, une « réconciliation » fermait les
segments restés ouverts.

**Base de données.**

- Environ **une ligne par membre et par minute de vocal**, et deux requêtes individuelles par membre et par
  minute. Avec quelques staffs en vocal les deux tiers de la journée, ça fait de l'ordre de dix mille lignes et
  vingt mille requêtes par jour.
- Les stats chargeaient toutes ces lignes en Python pour les additionner. Pour « depuis toujours » sur un membre
  très présent, ça représente des centaines de milliers de lignes au bout d'un an.
- Maintenant : une ligne par vraie session, et une requête groupée toutes les 2 minutes quelle que soit
  l'activité. L'addition se fait en SQL.

**Concurrence.** Le code faisait « y a-t-il un segment ouvert ? » puis `await` (écriture en base), puis
enregistrait le segment. Pendant cet `await`, un autre événement pouvait poser la même question, obtenir la
même réponse, et créer un second segment. L'un des deux restait ouvert en base sans que le bot ne le sache
plus. Comme un segment ouvert était compté « jusqu'à maintenant », **ce temps était compté deux fois jusqu'au
redémarrage suivant**. Le même schéma pouvait aussi faire planter un listener (`KeyError` sur un `del`).

**Rapport.**

- La fenêtre de rattrapage pouvait envoyer le rapport le lundi en calculant la *nouvelle* semaine (vide) :
  tout le monde en 🚨, avec ping.
- Le rapport pouvait dépasser la limite de 4000 caractères d'un message et ne jamais partir.
- Un panel de config resté ouvert pouvait écraser la date du dernier rapport et provoquer un renvoi.
- Le rapport pingait aussi les rôles du staff et les membres inactifs.

**À quelle fréquence le bug de double comptage arrivait-il ?** Pour en avoir une idée, l'ancien code et le
nouveau ont été rejoués dans une simulation (10 membres, 2 jours, activité aléatoire). Cette simulation est
**volontairement dure** : beaucoup plus d'événements qu'en réalité, base parfois lente, écritures qui échouent.
Elle grossit donc les problèmes, et ses chiffres ne sont pas ceux du vrai serveur :

- avec une base parfois lente (5 % des requêtes entre 0,5 et 3 s), l'ancien code a laissé des segments
  orphelins dans 33 simulations sur 40 ;
- avec une base toujours rapide (2 à 20 ms), encore 11 sur 40.

Sur le vrai serveur c'est sûrement plus rare. Mais le problème n'est pas la fréquence : **chaque occurrence
gonfle les stats d'un membre pendant des heures**, jusqu'au prochain redémarrage, sans que personne ne le voie.
Le nouveau code ne peut pas produire ce cas : rien n'est écrit en base en dehors du flush, et le flush ne laisse
jamais de session « ouverte » en base. Dans la même simulation, il n'a produit aucun chevauchement ni aucun
temps compté en trop (à quelques secondes près sur 2 jours, dues au délai de réaction du bot).
