<!--
Copyright (c) Communauté Les Frères Poulain
SPDX-License-Identifier: MIT
-->

# Extension Welcome

L'extension Welcome envoie automatiquement un message de bienvenue lorsqu'un nouveau membre rejoint un serveur Discord. Elle est conçue pour être simple à configurer et facile à utiliser.

## Fonctionnalités

- Message de bienvenue automatique lors de l'arrivée d'un membre
- Message personnalisable avec variables

## Utilisation

Pour utiliser l'extension Welcome, activez-la dans le fichier de configuration et configurez le message de bienvenue ainsi que le salon de destination.

Le message sera envoyé automatiquement dans le salon configuré chaque fois qu'un nouveau membre rejoint le serveur.

## Variables

Le message de bienvenue supporte les variables suivantes :

- `{user}` : Nom d'affichage du membre (surnom si défini)
- `{mention}` : Mention du membre
- `{username}` : Nom d'utilisateur Discord
- `{server}` : Nom du serveur
- `{member_count}` : Nombre total de membres
- `{created_at}` : Date de création du compte (format YYYY-MM-DD)
- `{joined_at}` : Date d'arrivée (format YYYY-MM-DD)

## Configuration

Exemple de configuration dans `config.yml` :

```yaml
extensions:
  welcome:
    enabled: true
    channel_id: 123456789  # ID du salon où envoyer le message
    message: "Bienvenue {mention} sur {server} !"
```

### Paramètres de configuration

- `enabled` : Activer ou désactiver l'extension (par défaut : `true`)
- `channel_id` : L'ID du salon Discord où envoyer le message de bienvenue
- `message` : Le message de bienvenue à envoyer (par défaut : `"Bienvenue {mention} sur {server} !"`)
