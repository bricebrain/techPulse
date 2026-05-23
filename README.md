# TechPulse API (FastAPI)

Backend FastAPI pour l'application frontend `apptechno`, orienté FinTech/ESG et prêt à intégrer des modules IA.

## Stack

- FastAPI
- Uvicorn
- Pydantic Settings

## Structure

```
app/
  api/routes/        # Endpoints REST
  core/              # Config environnement
  schemas/           # Contrats request/response
  services/          # Logique metier / services IA
  main.py            # Initialisation FastAPI
```

## Installation locale

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Lancer en local

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints disponibles

- `GET /` : statut service
- `GET /api/v1/health` : healthcheck
- `POST /api/v1/ai/prompt` : endpoint IA (mock)

Exemple payload:

```json
{
  "prompt": "Analyse ESG de cette entreprise"
}
```

## Deploiement Render

Pour un **Web Service** sur Render:

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Variables d'environnement conseillees:

- `APP_ENV=production`
- `ALLOWED_ORIGINS_RAW=https://ton-frontend.vercel.app`

## Prochaine etape IA

Le fichier `app/services/ai_service.py` est le point d'entree a remplacer pour brancher ton provider IA (OpenAI, Azure OpenAI, modele local, etc.).
