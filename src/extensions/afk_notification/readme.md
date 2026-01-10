<!--
Copyright (c) Communauté Les Frères Poulain
SPDX-License-Identifier: MIT
-->

# Extension Notification AFK

L'extension Notification AFK détecte et gère automatiquement les membres AFK (Away From Keyboard) dans les salons vocaux. Elle envoie des rappels périodiques et peut déconnecter les utilisateurs qui ne répondent pas dans un délai imparti.

## Fonctionnalités

- Détection automatique des membres AFK dans les salons vocaux
- Fonctionnement basé sur des plages horaires (heures de début/fin configurables)
- Messages de rappel périodiques aux "dormeurs" enregistrés
- Déconnexion automatique après expiration du délai
- Interaction utilisateur via boutons
- Filtrage par rôle (optionnel)
- Commandes administrateur pour gérer la liste des dormeurs

## Utilisation

Le bot surveille les membres dans les salons vocaux pendant la plage horaire configurée. À intervalles réguliers, il envoie des messages de rappel aux membres enregistrés comme "dormeurs". Si un membre ne répond pas en cliquant sur le bouton dans le délai imparti, il est automatiquement déconnecté du salon vocal.

## Commandes

Les commandes suivantes sont disponibles pour les administrateurs :

- `/dormeurs ajouter <membre>`
  Ajouter un membre à la liste des dormeurs.

- `/dormeurs supprimer <membre>`
  Retirer un membre de la liste des dormeurs.

- `/dormeurs lister`
  Afficher la liste des dormeurs enregistrés.

## Configuration

Exemple de configuration dans `config.yml` :

```yaml
extensions:
  afk_notification:
    enabled: true
    start_time: "09:00"  # Heure de début (format HH:MM)
    stop_time: "23:00"   # Heure de fin (format HH:MM)
    afk_reminder_every: 3600  # Intervalle entre les rappels (en secondes)
    afk_reminder_timeout: 300  # Délai avant déconnexion (en secondes)
    guild_id: 123456789  # ID du serveur Discord
    role_id: 987654321   # ID du rôle requis (optionnel)
```

### Paramètres de configuration

- `enabled` : Activer ou désactiver l'extension
- `start_time` : Heure de début de la surveillance AFK (format 24h HH:MM)
- `stop_time` : Heure de fin de la surveillance AFK (format 24h HH:MM)
- `afk_reminder_every` : Intervalle en secondes entre les messages de rappel (par défaut : 3600 = 1 heure)
- `afk_reminder_timeout` : Délai en secondes avant déconnexion d'un membre non réactif (par défaut : 300 = 5 minutes)
- `guild_id` : L'ID du serveur Discord où l'extension opère
- `role_id` : (Optionnel) Surveiller uniquement les membres avec ce rôle

## Fonctionnement

1. Le bot surveille les salons vocaux pendant la plage horaire configurée (start_time à stop_time)
2. À intervalles réguliers (afk_reminder_every), des messages de rappel sont envoyés aux dormeurs enregistrés
3. Les membres doivent cliquer sur un bouton dans le message de rappel pour confirmer qu'ils sont actifs
4. Si aucune réponse n'est reçue dans le délai imparti (afk_reminder_timeout), le membre est déconnecté
5. Les administrateurs peuvent gérer la liste des dormeurs via les commandes `/dormeurs`