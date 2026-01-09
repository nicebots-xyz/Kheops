# Khéops - Bot Communautaire Les Frères Poulain

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Pycord](https://img.shields.io/badge/discord-py--cord-blue.svg)](https://pycord.dev/)

Khéops est un bot Discord communautaire, développé par et pour la communauté des [Frères Poulain](https://www.youtube.com/@lesfrerespoulain).

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Fonctionnement](#-fonctionnement)
- [Installation rapide](#-installation-rapide)
- [Configuration](#-configuration)
- [Développement](#-développement)
- [Contribution](#-contribution)
- [License](#-license)

## Fonctionnalités

Khéops offre actuellement les fonctionnalités suivantes :

- **Message de bienvenue** : Accueil automatique des nouveaux membres avec un message de bienvenue
- **Notification AFK** : Système de détection et de gestion des membres AFK dans les salons vocaux
- **Commandes utilitaires** : Commandes de base comme `/ping` pour vérifier la latence du bot

### Extensions disponibles

Les fonctionnalités sont organisées en extensions modulaires dans `src/extensions/` :

| Extension          | Description                                              |
|--------------------|----------------------------------------------------------|
| `welcome`          | Messages de bienvenue                                    |
| `afk_notification` | Notifications et déconnexion automatique des membres AFK |
| `ping`             | Commande de test de latence                              |

## Fonctionnement

Khéops est basé sur [botkit](https://github.com/nicebots-xyz/botkit), un framework open-source pour créer des bots Discord.
Il utilise la librairie [py-cord](https://github.com/Pycord-Development/pycord) pour interagir avec l'API Discord.

### Architecture

Le bot est organisé de manière modulaire :

- **Extensions** : Chaque fonctionnalité est une extension indépendante dans `src/extensions/`
- **Configuration** : Système flexible avec fichiers YAML et variables d'environnement
- **Internationalisation** : Support multilingue via les fichiers de traduction

## Installation rapide

### Prérequis

- Python 3.11 ou plus récent
- PDM (gestionnaire de dépendances Python)
- Un token de bot Discord

### Installation en 3 étapes

1. **Cloner le projet**

   ```bash
   git clone https://github.com/nicebots-xyz/Kheops.git
   cd Kheops
   ```

2. **Installer les dépendances**

   ```bash
   pdm install
   ```

3. **Configurer le token**

   Créez un fichier `.env` à la racine :

   ```dotenv
   BOTKIT__BOT__TOKEN=votre_token_discord_ici
   ```

4. **Lancer le bot**
   ```bash
   pdm run start
   ```

## Configuration

Le bot possède deux configurations: une configuration publique et une configuration privée.

### Configuration publique

La configuration publique est effectuée dans le fichier [`config.yaml`](config.yaml), à la racine du projet. Elle contient \*\*\*

### Configuration privée

La configuration privée est effectuée dans le fichier `.env`, à la racine du projet, ou à travers les variables d'environnement.
Elle permet de ne pas partager les informations sensibles (token Discord, etc.).

Son fonctionnement est le suivant:

- le préfixe `BOTKIT__` est utilisé pour les variables d'environnement
- chaque `__` sépare les clés de valeurs
- les valeurs sont séparées par `=` (égal)
- toutes les clés sont en majuscules

Par exemple, la configuration yaml suivante:

```yaml
bot:
  token: "my_secret_token"
```

peut être définie dans le fichier `.env` comme suit:

```dotenv
BOTKIT__BOT__TOKEN=my_secret_token
```

Le fichier `.env` est prioritaire sur le fichier `config.yaml`. Cela signifie que si une même clé est définie dans les deux fichiers, la valeur du fichier `.env` sera utilisée.

### Configuration de l'extension AFK Notification

L'extension `afk_notification` permet de détecter et gérer automatiquement les membres AFK dans les salons vocaux. Voici un exemple de configuration :

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

**Fonctionnement** :
- Le bot surveille les membres dans les salons vocaux pendant la plage horaire définie
- À intervalles réguliers, il envoie un message de rappel aux membres enregistrés comme "dormeurs"
- Si le membre ne répond pas en cliquant sur le bouton dans le délai imparti, il est déconnecté automatiquement
- Les membres peuvent être enregistrés via les commandes `/dormeurs` par les administrateurs

**Commandes disponibles** (réservées aux administrateurs) :
- `/dormeurs ajouter <membre>` : Ajouter un membre à la liste des dormeurs
- `/dormeurs supprimer <membre>` : Retirer un membre de la liste des dormeurs
- `/dormeurs lister` : Afficher la liste des dormeurs enregistrés

### Obtenir un token Discord

Pour configurer votre bot, vous aurez besoin d'un token Discord :

1. Rendez-vous sur [discord.com/developers/applications](https://discord.com/developers/applications)
2. Créez une nouvelle application
3. Allez dans l'onglet **Bot** et créez un bot
4. Copiez le token et ajoutez-le dans votre fichier `.env`

> [!CAUTION]
> Ne partagez JAMAIS votre token ! C'est une information sensible.

## Développement

### Commandes de développement

Nous utilisons [Ruff](https://docs.astral.sh/ruff/) pour [linter](<https://fr.wikipedia.org/wiki/Lint_(logiciel)>) et formater le code.

```bash
# Vérifier le style du code
pdm run lint

# Formater automatiquement le code
pdm run format

# Lancer le bot en mode développement
pdm run start
```

### Workflow de développement

1. Créez une branche pour votre fonctionnalité : `git checkout -b ma-fonctionnalite`
2. Développez votre extension dans `src/extensions/`
3. Testez localement avec `pdm run start`
4. Vérifiez le code avec `pdm run lint`
5. Committez vos changements : `git commit -m "Description claire"`
6. Poussez votre branche : `git push origin ma-fonctionnalite`
7. Créez une Pull Request sur GitHub

## Contribution

Nous accueillons chaleureusement les contributions ! Que vous soyez débutant ou expérimenté, vous pouvez nous aider.

### Comment contribuer ?

1. **Lisez le guide** : Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour un guide détaillé
2. **Choisissez une tâche** : Regardez les [issues ouvertes](https://github.com/nicebots-xyz/Kheops/issues)
3. **Proposez une idée** : Ouvrez une issue pour discuter de votre proposition
4. **Créez une extension** : Développez une nouvelle fonctionnalité

### Types de contributions acceptées

- ✅ Nouvelles extensions dans `src/extensions/`
- ✅ Améliorations des extensions existantes
- ✅ Corrections de bugs
- ✅ Amélioration de la documentation
- ✅ Traductions

### Règles importantes

- **Compréhension du code** : Vous devez comprendre le code que vous soumettez
- **Contributions AI** : Les contributions entièrement générées par IA peuvent être rejetées
- **Ouverture** : Soyez prêt à recevoir des retours et des demandes de modification
- **Documentation** : Consultez [docs.pycord.dev](https://docs.pycord.dev) pour apprendre Pycord

Pour plus de détails, consultez notre [guide de contribution](CONTRIBUTING.md).

## Ressources utiles

- **Documentation Pycord** : [docs.pycord.dev](https://docs.pycord.dev)
- **Botkit Framework** : [github.com/nicebots-xyz/botkit](https://github.com/nicebots-xyz/botkit)
- **Discord API** : [discord.com/developers/docs](https://discord.com/developers/docs)
- **Python PDM** : [pdm-project.org](https://pdm-project.org/)

## License

Khéops est sous licence MIT. Les crédits sont disponibles dans le fichier [pyproject.toml](pyproject.toml). Plus d'informations sur la licence sont disponibles dans le fichier [LICENSE](LICENSE).
