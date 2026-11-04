<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz -->

# poll

Crée des sondages natifs Discord avec une date de fin précise à l'heure près. L'interface Discord
n'offre que des durées prédéfinies (1 h, 4 h, 8 h, 24 h, 3 jours, 1 semaine, 2 semaines), alors que
l'API accepte n'importe quelle durée entière en heures entre 1 et 768 (32 jours).

## Utilisation

`/poll` (`/sondage` en français), réservé par défaut aux administrateurs, ouvre un panneau éphémère :

- **Question et fin** : modale avec la question (300 caractères max), la date (`JJ/MM/AAAA`),
  l'heure (`HH:MM`) et l'option « réponses multiples ».
- **Ajouter une réponse** : modale avec un emoji optionnel et le texte de la réponse
  (55 caractères max, 10 réponses max). L'emoji peut être l'ID d'un emoji personnalisé
  (`123456789012345678`), sa mention (`<:nom:id>`), l'emoji unicode lui-même ou un alias
  (`:jack_o_lantern:`).
- **Modifier / Supprimer une réponse** : menus déroulants listant les réponses existantes.
- **Envoyer le sondage** : publie le sondage dans le salon courant.

## Calcul de la durée

Discord ne prend qu'une durée en heures. La durée retenue est le plus petit nombre d'heures entier
qui atteint ou dépasse la date demandée : le sondage ne se termine jamais avant elle.
Par exemple, une fin demandée dans 2 h 01 donne une durée de 3 h. La durée est recalculée au moment
de l'envoi, et le panneau affiche la fin réelle (horodatage Discord, dans le fuseau du lecteur).

## Configuration

```yaml
extensions:
  poll:
    enabled: true
    timezone: "Europe/Paris" # Fuseau IANA dans lequel les dates saisies sont interprétées
```

Le bot a besoin de la permission « Envoyer des sondages » dans le salon. Une erreur renvoyée par
Discord (permission manquante, emoji inutilisable...) est affichée dans le panneau sans perdre le
brouillon.
