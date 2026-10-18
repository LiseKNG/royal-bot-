# Déploiement sur Railway

1. Envoyer le contenu de ce dossier dans un dépôt GitHub privé (ne jamais envoyer `.env`).
2. Dans Railway, créer un projet depuis ce dépôt.
3. Ajouter un service PostgreSQL via **New → Database → PostgreSQL**.
4. Dans les variables du service application, ajouter :
   - `BOT_TOKEN` = token obtenu auprès de @BotFather
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (adapter `Postgres` au nom exact du service DB)
   - `APP_SECRET` = une chaîne aléatoire longue
   - `WEB_ADMIN_TOKEN` = un autre secret aléatoire long
   - `PORT` = `8000` (optionnel, un port Railway fourni sera utilisé automatiquement)
   - `LOG_LEVEL` = `INFO`
5. Déployer le service. Le dépôt contient un Dockerfile détecté automatiquement.
6. Dans les paramètres du service application, générer un domaine public.
7. Vérifier `https://TON-DOMAINE/health` puis ouvrir `/docs`.
8. Envoyer `/start` au bot Telegram, puis l'ajouter à un groupe. En tant qu'administrateur, lancer `/register_space` dans ce groupe.

Important :
- Le service de l'application doit rester en exécution permanente, car il lance le polling Telegram.
- N'exécute pas plusieurs réplicas de cette même application en polling avec le même token : ils peuvent se gêner.
- Ne mets jamais `BOT_TOKEN`, `APP_SECRET` ou `WEB_ADMIN_TOKEN` dans GitHub.
- La page web actuelle est une maquette et l'API utilise un jeton partagé. Ne considère pas l'interface comme sécurisée pour des clients publics avant d'ajouter une vraie authentification.
- Le nom du service PostgreSQL dans la référence `${{Postgres.DATABASE_URL}}` doit correspondre au nom réel affiché sur Railway.
