<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz -->

# stats_staff

Suivi des quotas d'activité hebdomadaires du staff (messages + temps vocal valide).

## Fonctionnement

- Les messages ne sont comptés que dans les salons désignés comme "salons suivis (messages)".
- Le temps vocal n'est compté que dans les salons désignés comme "salons suivis (vocal)", et
  seulement pendant que le membre n'est ni muet ni sourd (self ou serveur) et qu'au moins une
  autre personne (non-bot) est présente dans le salon.
- Chaque rôle de staff peut avoir un quota hebdomadaire : un nombre d'heures de vocal et/ou un
  nombre de messages, combinés avec une condition "OU" ou "ET" :
  - **OU** : les deux activités se combinent proportionnellement. Par exemple, sur un quota
    "4h de vocal OU 100 messages", faire 2h de vocal (50 % du seuil) et 50 messages (50 % du
    seuil) remplit le quota (50 % + 50 % = 100 %), même si aucun des deux seuils n'est atteint
    seul.
  - **ET** : les deux seuils sont normalement requis en entier, mais un manque sur l'un peut être
    compensé par un surplus sur l'autre, à un taux de pénalité configurable (125 % par défaut,
    réglable dans `/stats-staff-admin config`, appliqué à tous les quotas ET du serveur). Par
    exemple sur "6h de vocal ET 100 messages" : sauter entièrement les messages demande
    6h + 125 % × 6h = 13.5h de vocal ; ne faire que 3h de vocal (50 % du seuil, soit un manque de
    50 %) demande 100 + 125 % × 50 % × 100 = 162.5 messages pour compenser. Si les deux critères
    sont en dessous de leur seuil, le quota échoue dans tous les cas.
- Chaque dimanche à 23:59 (Europe/Paris), un rapport récapitulatif (tous les staffs, succès et
  échecs) est posté dans le salon de rapport configuré. Les membres n'ayant fait **ni message ni
  vocal** de la semaine sont marqués 🚨 (au lieu de ❌) et, si un rôle "Responsable Staff" est
  configuré, un bloc dédié le ping en haut du rapport avec la liste de ces membres — c'est un
  signal différent d'un simple quota manqué.
- La "tendance vs semaine dernière" (dans `/stats-staff moi`/`voir` et le rapport) compare toujours
  des périodes de durée égale : la semaine en cours jusqu'à maintenant contre la semaine dernière
  jusqu'au même jour/heure, pas la semaine dernière complète — ça évite une fausse baisse en
  tout début de semaine.
- Les données brutes (messages, segments de vocal) sont conservées indéfiniment, ce qui permet de
  consulter n'importe quelle période a posteriori.
- Le suivi vocal checkpointe les sessions en cours toutes les minutes (ferme et rouvre un nouveau
  segment) : en cas de crash ou de redémarrage, au plus une minute de vocal peut être mal comptée,
  au lieu de tout le temps d'indisponibilité du bot.

## Commandes

- `/stats-staff aide` — explique le fonctionnement des modes OU/ET (avec la pénalité de
  substitution actuelle du serveur), et le détail chiffré du quota du membre qui l'utilise s'il en
  a un. Ouvert à tout le monde.
- `/stats-staff moi [periode]` — mes propres statistiques (semaine en cours par défaut), réservé
  aux membres ayant un rôle avec quota configuré.
- `/stats-staff voir <membre> [periode]` — statistiques d'un autre membre, réservé aux
  administrateurs et au rôle "Responsable Staff" configuré.
- `/stats-staff-admin config` — panel de configuration interactif (rôle responsable, salon de
  rapport, salons suivis, quotas par rôle). Réservé par défaut aux administrateurs Discord ; un
  administrateur peut ensuite déléguer l'accès à cette commande au rôle "Responsable Staff" via
  les permissions de commande du serveur (Paramètres du serveur → Intégrations).

## Membres avec plusieurs rôles quota

Si un membre a plusieurs rôles ayant chacun un quota configuré, le bot ne peut pas deviner lequel
appliquer. Dans `/stats-staff-admin config` → "Gérer les quotas par rôle" →
"Assigner les membres à rôles multiples", ces membres sont listés avec un marqueur ⚠️ tant qu'ils
n'ont pas été assignés explicitement à l'un de leurs rôles ; cette assignation est ensuite utilisée
pour leurs stats et pour le rapport hebdomadaire (qui ne les compte alors que sous ce rôle-là, pas
sous chacun). Sans assignation, le bot retombe sur le premier rôle correspondant trouvé — à éviter
pour des stats fiables.

## Limitations connues

- Aucune action de modération n'est comptabilisée : Khéops n'a pas de commandes de modération
  propres, donc seules les actions faites via le bot pourraient être suivies de façon fiable —
  hors scope pour l'instant.
