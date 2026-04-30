# Master72 Demo

Temporary demo landing page for a handyman service in Tyumen with Telegram lead delivery.

## Local launch

```powershell
python server.py
```

Open `http://127.0.0.1:4173`.

## Required environment variables

Create a local `.env` file based on `.env.example`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Render deploy

1. Push this folder to a GitHub repository.
2. In Render, choose `New +` -> `Blueprint`.
3. Connect the repository and deploy `render.yaml`.
4. In Render service settings, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Wait for the build to finish and open the `onrender.com` URL.

## Notes

- Render free web services can spin down after inactivity.
- The first request after idle can take around a minute.
