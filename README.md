# Telegram Community Suite

Base multi-tenant pour gérer plusieurs propriétaires, groupes et chaînes Telegram depuis un bot Telegram et un tableau de bord web.

## Fonctionnalités de cette base
- Bot Telegram avec aiogram 3 : `/start`, `/help`, `/id`, `/profile`, `/spaces`, `/stats`, `/warn`, `/ban`, `/unban`.
- API et tableau de bord FastAPI avec connexion par jeton administrateur.
- PostgreSQL + SQLAlchemy async.
- Modèle multi-propriétaire : chaque espace est rattaché à un propriétaire (`owner_telegram_id`) et les accès sont vérifiés côté API.
- Profils de membres indexés par identifiant Telegram, pseudonyme/nom mis à jour au fil des événements.
- Journal d'événements et de modération.
- Docker Compose pour démarrer PostgreSQL et l'application.
- Webhook/polling : cette version utilise le polling pour faciliter le démarrage.

## Limites importantes de Telegram
Le bot ne peut pas découvrir tous les membres d'un groupe ou tous les abonnés silencieux d'une chaîne. Il apprend les profils lors d'interactions, d'événements d'arrivée/départ et des mises à jour que Telegram lui transmet. Dans les groupes, ajoute le bot et donne-lui uniquement les droits nécessaires. Pour bannir, il doit être administrateur avec le droit de bannir. Pour recevoir tous les messages de groupe, configure le mode confidentialité via BotFather si c'est réellement nécessaire. Les chaînes et les groupes n'exposent pas les mêmes événements.

## Démarrage rapide
1. Crée un bot avec `@BotFather`.
2. Copie `.env.example` vers `.env` et renseigne `BOT_TOKEN` et `APP_SECRET`.
3. Lance `docker compose up --build`.
4. Ouvre `http://localhost:8000`.
5. Envoie `/start` au bot. L'identifiant Telegram de l'utilisateur qui envoie `/start` est créé comme propriétaire initial si aucun propriétaire n'existe.
6. Depuis le bot, ajoute les groupes/chaînes avec `/register_space` en étant propriétaire. Pour que le bot puisse reconnaître l'espace, ajoute-le d'abord à cet espace. La commande doit être exécutée dans l'espace à enregistrer.

## Variables
- `BOT_TOKEN`: token de BotFather.
- `DATABASE_URL`: URL SQLAlchemy async, par défaut PostgreSQL dans Docker.
- `APP_SECRET`: secret long et aléatoire utilisé pour signer les sessions web.
- `WEB_ADMIN_TOKEN`: jeton facultatif pour protéger les routes API d'administration; utiliser un secret différent en production.
- `PUBLIC_BASE_URL`: URL publique si tu passes ultérieurement en webhook.
- `LOG_LEVEL`: niveau de journalisation.

## Sécurité avant production
Cette base est un socle fonctionnel, pas un produit audité. Avant une mise en production publique :
- utilise HTTPS derrière un reverse proxy ;
- remplace le jeton partagé par une authentification Telegram Login/OIDC ou une vraie gestion de sessions ;
- limite les tentatives de connexion, ajoute CSRF, sauvegardes et rotation des secrets ;
- configure migrations Alembic et supervision ;
- ajoute tests automatisés, politique de rétention et consentement adapté ;
- n'accorde pas des droits administrateur plus larges que nécessaire.

## Commandes
- `/start`, `/help`, `/id`, `/profile`, `/spaces`, `/stats`
- `/register_space` dans le groupe/la chaîne (enregistrable si le bot reçoit la commande)
- `/warn <raison>`
- `/ban [raison]` (répondre au message d'un membre)
- `/unban <user_id>`

Les commandes de modération sont réservées aux administrateurs Telegram de l'espace. Les commandes qui exigent un message ciblé doivent être utilisées en réponse au message concerné.

## Structure
- `app/config.py`: configuration
- `app/db.py`: SQLAlchemy et sessions
- `app/models.py`: modèles
- `app/services.py`: opérations communes et contrôles d'accès
- `app/bot.py`: handlers aiogram
- `app/web.py`: tableau de bord et API FastAPI
- `app/main.py`: démarrage web + polling
- `Dockerfile`, `docker-compose.yml`: déploiement local
