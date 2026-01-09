``# Politique de Sécurité

## Versions supportées

Nous supportons actuellement la dernière version du bot Khéops déployée sur le serveur Discord des Frères Poulain.

## Signaler une vulnérabilité

La sécurité de Khéops et de la communauté des Frères Poulain est importante pour nous. Si vous découvrez une vulnérabilité de sécurité, nous apprécions votre aide pour la divulguer de manière responsable.

### Comment signaler une vulnérabilité

> [!IMPORTANT]
> **Ne créez PAS d'issue publique** sur GitHub pour les vulnérabilités de sécurité.

Pour signaler une vulnérabilité de sécurité :

1. **Contactez un administrateur technique** via message privé (DM) sur le serveur Discord des Frères Poulain
2. Incluez les informations suivantes dans votre rapport :
   - Description détaillée de la vulnérabilité
   - Étapes pour reproduire le problème
   - Impact potentiel de la vulnérabilité
   - Suggestions de correction (si vous en avez)

### Types de vulnérabilités concernées

Veuillez signaler les problèmes suivants :

- **Injection de code** : SQL injection, command injection, etc.
- **Failles d'authentification** : Contournement de permissions Discord, accès non autorisé
- **Exposition de données sensibles** : Tokens, clés API, informations utilisateur
- **Failles de validation** : XSS, CSRF dans les commandes du bot
- **Déni de service** : Bugs permettant de crash le bot ou de le surcharger
- **Élévation de privilèges** : Obtention de permissions non autorisées

### Ce qui n'est PAS une vulnérabilité de sécurité

Les éléments suivants ne sont **pas** considérés comme des vulnérabilités de sécurité :

- Bugs fonctionnels sans impact sur la sécurité (créez une issue normale)
- Suggestions de nouvelles fonctionnalités
- Questions sur la configuration ou l'utilisation
- Problèmes liés à Discord lui-même (signalez à Discord)

### Délai de réponse

- **Accusé de réception** : Nous accuserons réception de votre rapport dans les 48 heures
- **Évaluation initiale** : Nous évaluerons la gravité dans les 7 jours
- **Correction** : Le délai dépend de la gravité et de la complexité

### Divulgation responsable

Nous vous demandons de :

- Nous donner un délai raisonnable pour corriger la vulnérabilité avant toute divulgation publique
- Ne pas exploiter la vulnérabilité au-delà de ce qui est nécessaire pour la démonstration
- Ne pas accéder, modifier ou supprimer des données appartenant à d'autres utilisateurs

### Reconnaissance

Nous remercions les chercheurs en sécurité qui signalent des vulnérabilités de manière responsable. Avec votre accord, nous vous mentionnerons dans nos notes de version lors de la correction.

## Bonnes pratiques de sécurité

Si vous hébergez votre propre instance de Khéops :

### Protection des tokens et secrets

> [!CAUTION]
> Ne commitez JAMAIS vos tokens, clés API ou autres secrets dans Git.

- Utilisez toujours le fichier `.env` pour les informations sensibles
- Assurez-vous que `.env` est dans votre `.gitignore`
- Ne partagez jamais votre token Discord publiquement
- Régénérez immédiatement votre token s'il a été exposé

### Permissions Discord

- Accordez uniquement les permissions nécessaires au bot
- Utilisez `default_member_permissions` pour restreindre l'accès aux commandes sensibles
- Vérifiez toujours les permissions avant d'effectuer des actions de modération

### Mises à jour

- Maintenez vos dépendances à jour avec `pdm update`
- Surveillez les alertes de sécurité de Pycord et Botkit
- Testez les mises à jour dans un environnement de développement avant la production

### Validation des entrées

- Validez toujours les entrées utilisateur dans vos extensions
- Utilisez les validateurs de Pycord pour les arguments de commandes
- Échappez les données avant de les afficher ou de les stocker

## Ressources

- [Documentation Pycord Security](https://docs.pycord.dev)
- [Discord Developer Terms](https://discord.com/developers/docs/policies-and-agreements/developer-terms-of-service)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

## Contact

Pour toute question concernant cette politique de sécurité, contactez un administrateur technique sur le serveur Discord des Frères Poulain.
