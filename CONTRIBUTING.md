# Guide de Contribution

Bienvenue ! Nous sommes ravis que vous souhaitiez contribuer à Khéops. Ce guide vous accompagnera pas à pas dans le processus de contribution, que vous soyez débutant ou expérimenté en développement.

## Table des matières

1. [Avant de commencer](#avant-de-commencer)
2. [Types de contributions acceptées](#types-de-contributions-acceptées)
3. [Prérequis](#prérequis)
4. [Configuration de l'environnement](#configuration-de-lenvironnement)
5. [Créer votre première contribution](#créer-votre-première-contribution)
6. [Standards de code](#standards-de-code)
7. [Processus de révision](#processus-de-révision)
8. [Ressources utiles](#ressources-utiles)
9. [Besoin d'aide ?](#besoin-daide-)

## Avant de commencer

### Philosophie du projet

Khéops est un projet communautaire où la qualité et la compréhension du code sont essentielles. Nous valorisons :

- **La compréhension** : Vous devez comprendre le code que vous contribuez
- **La qualité** : Le code doit être propre, testé et maintenable
- **L'ouverture** : Soyez prêt à recevoir des retours constructifs et des demandes de modification
- **L'apprentissage** : Les erreurs font partie du processus, nous sommes là pour vous aider

### Important : Contributions générées par IA

> [!WARNING]
> Les contributions entièrement générées par des outils d'IA (ChatGPT, Copilot, etc.) peuvent être **rejetées à tout moment**.

Pourquoi ? Parce que nous attendons de chaque contributeur qu'il :

- Comprenne le code qu'il soumet
- Puisse expliquer ses choix techniques
- Soit capable de maintenir et déboguer sa contribution

**Utiliser l'IA comme assistant est acceptable**, mais vous devez :

- Relire et comprendre chaque ligne de code générée
- Adapter le code au contexte du projet
- Être capable d'expliquer le fonctionnement de votre contribution

## Types de contributions acceptées

### Extensions

Les modifications aux extensions sous `src/extensions/` sont les contributions principales acceptées. Une extension peut :

- Ajouter de nouvelles commandes Discord
- Implémenter des fonctionnalités pour le serveur
- Réagir à des événements Discord (messages, réactions, etc.)

### Autres contributions

- Corrections de bugs dans les extensions existantes
- Améliorations de documentation
- Corrections de fautes de frappe
- Améliorations des messages d'erreur

### Contributions généralement non acceptées

- Modifications du cœur de Botkit (à soumettre sur [botkit](https://github.com/nicebots-xyz/botkit))
- Changements de configuration globale sans discussion préalable
- Fonctionnalités sans rapport avec les besoins de la communauté

> [!TIP]
> Avant de commencer une grosse contribution, ouvrez une issue pour discuter de votre idée !

## Prérequis

### Connaissances recommandées

Pas de panique si vous êtes débutant ! Voici ce qui vous sera utile :

- **Python de base** : Variables, fonctions, classes (niveau intermédiaire)
- **Git de base** : Clone, commit, push, pull request
- **Discord** : Comprendre comment fonctionne Discord (serveurs, canaux, rôles, permissions)

### Logiciels requis

1. **Python 3.11 ou plus récent**
   - Téléchargez depuis [python.org](https://www.python.org/downloads/)
   - Vérifiez l'installation : `python --version`

2. **PDM** (gestionnaire de dépendances)
   - Installation : `pip install pdm`
   - Vérifiez l'installation : `pdm --version`

3. **Git**
   - Installation : [git-scm.com](https://git-scm.com/downloads)
   - Vérifiez l'installation : `git --version`

4. **Un éditeur de code** (au choix)
   - [VS Code](https://code.visualstudio.com/) (recommandé pour les débutants)
   - [PyCharm](https://www.jetbrains.com/pycharm/)
   - Ou tout autre éditeur de votre choix

## Configuration de l'environnement

### 1. Fork et clone du projet

Un "fork" est votre propre copie du projet sur GitHub.

1. Rendez-vous sur [github.com/nicebots-xyz/Kheops](https://github.com/nicebots-xyz/Kheops)
2. Cliquez sur le bouton **Fork** en haut à droite
3. Clonez votre fork sur votre ordinateur :

```bash
git clone https://github.com/VOTRE-NOM-UTILISATEUR/Kheops.git
cd Kheops
```

### 2. Installation des dépendances

PDM va installer toutes les bibliothèques Python nécessaires :

```bash
pdm install
```

Cette commande peut prendre quelques minutes la première fois.

### 3. Configuration du bot

Pour tester votre bot localement, vous aurez besoin d'un token Discord.

#### Créer une application Discord

1. Allez sur [discord.com/developers/applications](https://discord.com/developers/applications)
2. Cliquez sur **New Application**
3. Donnez-lui un nom (ex: "Khéops Dev")
4. Allez dans l'onglet **Bot**
5. Cliquez sur **Reset Token** et copiez le token

> [!CAUTION]
> Ne partagez JAMAIS ce token ! C'est comme un mot de passe.

#### Configurer le fichier .env

Créez un fichier `.env` à la racine du projet :

```bash
# Sur Linux/Mac
touch .env

# Sur Windows
type nul > .env
```

Ajoutez-y votre token :

```dotenv
BOTKIT__BOT__TOKEN=votre_token_ici
```

#### Inviter le bot sur votre serveur de test

1. Dans le Developer Portal, allez dans **OAuth2** > **URL Generator**
2. Cochez les scopes : `bot` et `applications.commands`
3. Choisissez les permissions nécessaires (ou "Administrator" pour les tests)
4. Copiez l'URL générée et ouvrez-la dans votre navigateur
5. Sélectionnez votre serveur de test

### 4. Tester que tout fonctionne

Lancez le bot :

```bash
pdm run start
```

Si tout fonctionne, vous devriez voir le bot en ligne sur votre serveur Discord !

Pour arrêter le bot : `Ctrl+C`

## Créer votre première contribution

### 1. Créer une branche

Une branche est une version parallèle du code où vous pouvez travailler sans affecter le code principal.

```bash
git checkout -b ajout-commande-hello
```

Nommez votre branche de façon descriptive : `ajout-X`, `correction-Y`, `amelioration-Z`

### 2. Comprendre la structure d'une extension

Les extensions se trouvent dans `src/extensions/`. Voici un exemple simple :

```
src/extensions/
└── mon_extension/
    ├── __init__.py          # Point d'entrée (requis)
    ├── main.py              # Logique principale
    └── config.yaml          # Configuration (optionnel)
```

#### Exemple d'extension simple

Créons une extension "hello" qui répond "Bonjour !" quand on tape `/hello`.

**Fichier `src/extensions/hello/__init__.py`** :

```python
from . import main

def setup(bot):
    """Fonction appelée par Botkit pour charger l'extension"""
    bot.add_cog(main.HelloCog(bot))
```

**Fichier `src/extensions/hello/main.py`** :

```python
import discord
from discord.ext import commands


class HelloCog(commands.Cog):
    """Extension qui dit bonjour"""

    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(
        name="hello",
        description="Le bot vous salue"
    )
    async def hello(self, ctx: discord.ApplicationContext):
        """Commande /hello"""
        await ctx.respond("Bonjour ! 👋")


# Ne pas oublier cette fonction
def setup(bot):
    bot.add_cog(HelloCog(bot))
```

### 3. Tester votre extension

1. Lancez le bot : `pdm run start`
2. Sur Discord, tapez `/hello`
3. Vérifiez que le bot répond correctement

### 4. Apprendre de la documentation

Pour créer des extensions plus complexes, consultez la documentation Pycord :

- **Documentation officielle** : [docs.pycord.dev](https://docs.pycord.dev)
- **Commandes slash** : [docs.pycord.dev/en/stable/api/application_commands.html](https://docs.pycord.dev/en/stable/api/application_commands.html)
- **Événements** : [docs.pycord.dev/en/stable/api/events.html](https://docs.pycord.dev/en/stable/api/events.html)
- **Exemples** : [github.com/Pycord-Development/pycord/tree/master/examples](https://github.com/Pycord-Development/pycord/tree/master/examples)

### 5. Vérifier la qualité du code

Avant de soumettre, assurez-vous que votre code respecte nos standards :

```bash
# Vérifier les erreurs de style
pdm run lint

# Formater automatiquement le code
pdm run format
```

Si `pdm run lint` affiche des erreurs, corrigez-les avant de continuer.

## Standards de code

### Style de code

Nous utilisons [Ruff](https://docs.astral.sh/ruff/) pour garantir un code uniforme.

**Règles importantes** :

- Indentation : 4 espaces (pas de tabs)
- Longueur de ligne : maximum 100 caractères
- Noms de variables : `snake_case` (ex: `ma_variable`)
- Noms de classes : `PascalCase` (ex: `MaClasse`)
- Noms de constantes : `UPPER_CASE` (ex: `MA_CONSTANTE`)

### Documentation

Documentez vos fonctions avec des docstrings :

```python
async def ma_commande(self, ctx, argument: str):
    """
    Description courte de la commande.

    Args:
        ctx: Le contexte Discord
        argument: Description de l'argument
    """
    # Votre code ici
```

### Gestion des erreurs

Toujours gérer les cas d'erreur possibles :

```python
@discord.slash_command()
async def ma_commande(self, ctx):
    try:
        # Code qui peut échouer
        resultat = operation_risquee()
        await ctx.respond(f"Succès : {resultat}")
    except Exception as e:
        # Message d'erreur clair pour l'utilisateur
        await ctx.respond("Une erreur s'est produite. Réessayez plus tard.", ephemeral=True)
        # Log l'erreur pour le débogage
        logger.exception(f"Erreur dans ma_commande")
```

### Permissions Discord

Vérifiez toujours les permissions avant d'effectuer des actions :

```python
@discord.slash_command(default_member_permissions=discord.Permissions(manage_messages=True))
async def moderation(self, ctx):
    """Commande réservée aux modérateurs"""
    await ctx.respond("Action de modération effectuée")
```

## Processus de révision

### 1. Commit et push

Une fois votre code prêt :

```bash
# Ajouter vos fichiers modifiés
git add src/extensions/mon_extension/

# Créer un commit avec un message clair
git commit -m "Ajout de l'extension hello pour saluer les utilisateurs"

# Envoyer sur votre fork
git push origin ajout-commande-hello
```

**Messages de commit clairs** :

- ✅ "Ajout de la commande /stats pour afficher les statistiques"
- ✅ "Correction du bug d'affichage dans l'extension welcome"
- ❌ "fix"
- ❌ "update"

### 2. Créer une Pull Request

1. Allez sur votre fork GitHub
2. Cliquez sur **Compare & pull request**
3. Remplissez le formulaire :
   - **Titre** : Description concise (ex: "Ajout de l'extension hello")
   - **Description** : Expliquez ce que fait votre contribution et pourquoi

**Template de description** :

```markdown
## Description

Ajout d'une nouvelle extension qui permet aux utilisateurs de...

## Type de changement

- [ ] Nouvelle fonctionnalité
- [ ] Correction de bug
- [ ] Amélioration de documentation

## Tests effectués

- [x] Testé la commande /hello sur un serveur de développement
- [x] Vérifié que le bot répond correctement
- [x] Exécuté `pdm run lint` sans erreurs

## Checklist

- [x] J'ai lu et compris le code que je soumets
- [x] Mon code respecte les standards du projet
- [x] J'ai testé mes modifications
- [x] Je suis prêt à recevoir des retours et apporter des modifications
```

### 3. Attendre la révision

Un mainteneur va examiner votre code. Attendez-vous à :

- **Des questions** : Pour comprendre vos choix
- **Des suggestions** : Pour améliorer le code
- **Des demandes de modification** : C'est normal et positif !

**Comment réagir aux retours** :

- ✅ Posez des questions si vous ne comprenez pas
- ✅ Acceptez les critiques constructives
- ✅ Expliquez vos choix de façon respectueuse
- ❌ Ne le prenez pas personnellement

### 4. Apporter des modifications

Si des changements sont demandés :

```bash
# Faites vos modifications
git add .
git commit -m "Prise en compte des retours: amélioration de la gestion d'erreurs"
git push origin ajout-commande-hello
```

La Pull Request sera automatiquement mise à jour !

### 5. Fusion

Une fois approuvée, votre contribution sera fusionnée. Félicitations ! 🎉

## Ressources utiles

### Documentation

- **Pycord** : [docs.pycord.dev](https://docs.pycord.dev) - Documentation officielle de la bibliothèque
- **Discord API** : [discord.com/developers/docs](https://discord.com/developers/docs) - Documentation de l'API Discord
- **Botkit** : [github.com/nicebots-xyz/botkit](https://github.com/nicebots-xyz/botkit) - Framework utilisé par Khéops

### Tutoriels Python

- **Python.org** : [docs.python.org/fr/3/tutorial/](https://docs.python.org/fr/3/tutorial/) - Tutoriel officiel Python
- **OpenClassrooms** : Cours Python gratuits en français
- **Real Python** : Tutoriels avancés (en anglais)

### Git et GitHub

- **Guide Git** : [git-scm.com/book/fr/v2](https://git-scm.com/book/fr/v2) - Livre Pro Git en français
- **GitHub Docs** : [docs.github.com/fr](https://docs.github.com/fr) - Documentation GitHub

### Exemples de code

Regardez les extensions existantes dans `src/extensions/` pour vous inspirer :

- `src/extensions/ping/` - Extension simple
- `src/extensions/welcome/` - Extension avec configuration
- `src/extensions/help/` - Extension plus complexe

## Besoin d'aide ?

### Avant de demander de l'aide

1. Relisez ce guide attentivement
2. Consultez la documentation Pycord
3. Regardez les extensions existantes comme exemples
4. Cherchez l'erreur sur Google (souvent quelqu'un a eu le même problème)

### Où poser vos questions

- **Issues GitHub** : Pour les bugs ou suggestions de fonctionnalités
- **Discussions GitHub** : Pour les questions générales
- **Serveur Discord** : Pour discuter avec la communauté

### Comment poser une bonne question

Incluez toujours :

1. **Ce que vous essayez de faire** : "Je veux créer une commande qui..."
2. **Ce que vous avez essayé** : "J'ai écrit ce code..."
3. **Le problème rencontré** : "J'obtiens cette erreur..."
4. **Les messages d'erreur complets** : Copiez-collez tout le message

**Exemple** :

```
Je veux créer une commande /roll qui lance un dé.

Voici mon code :
[votre code]

Mais quand je lance le bot, j'obtiens cette erreur :
[message d'erreur complet]

J'ai essayé de chercher sur Google mais je ne comprends pas ce que signifie "xyz".
```

## Remerciements

Merci de contribuer à Khéops ! Chaque contribution, petite ou grande, aide à améliorer le bot pour toute la communauté des Frères Poulain. 💙

N'oubliez pas : tout le monde a été débutant un jour. Posez vos questions, apprenez de vos erreurs, et amusez-vous en codant !
