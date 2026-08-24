# SmartMail AI — Intelligent Email Client

**Live Demo:** [https://smartmail-gemini.vercel.app/](https://smartmail-gemini.vercel.app/)

A standalone, AI-powered email client built on Flask that integrates with Zoho Mail. It analyzes emails in real-time using AI to provide summaries, tone classification, urgency detection, key points, and smart reply suggestions — all visible before you even open an email.

## Features

- **Zoho Mail Integration**: OAuth2-based authentication with automatic token refresh. Fetches inbox messages, folders, and full email content.
- **AI-Powered Pre-Open Intelligence**: Each email is analyzed for:
  - Summary (1-2 sentence overview)
  - Tone (Positive / Neutral / Negative)
  - Urgency (High / Medium / Low)
  - Key Points (action items and important details)
  - Suggested Reply (professional draft response)
- **Modern Three-Pane UI**: Zoho Mail-inspired interface with sidebar navigation, inbox list with AI badges, and a reading panel with analysis.
- **Smart Filtering**: Filter emails by urgency, tone, or analysis status. Full-text search across subjects, senders, and summaries.
- **Analytics Dashboard**: Visual overview with charts for sentiment distribution, urgency levels, and a searchable analysis history stream.
- **Firebase Persistence**: All analysis results are cached in Firestore to prevent duplicate processing and enable historical review.
- **Keyboard Navigation**: Arrow keys / j/k to navigate, Enter to select, Escape to close.

## Architecture

```
smartmail-main-gmail/
├── app.py                      # Flask routes (mail client + dashboard + API)
├── analyze.py                  # AI analysis engine (OpenRouter with multi-model failover)
├── zoho_service.py             # Zoho Mail API integration
├── services/
│   ├── __init__.py
│   ├── analysis_service.py     # Orchestration: fetch → clean → analyze → cache
│   └── firebase_service.py     # Firestore CRUD operations
├── static/
│   ├── css/
│   │   └── style.css           # Design system (dark theme)
│   └── js/
│       ├── mail.js             # Mail client interactivity
│       └── dashboard.js        # Dashboard charts & stats
├── templates/
│   ├── mail.html               # Three-pane mail client
│   └── dashboard.html          # Analytics dashboard
├── requirements.txt
├── Procfile
└── README.md
```

## How It Works

1. **User opens the app** → The inbox loads emails from Zoho Mail API
2. **Cached analysis** is displayed instantly as badges (tone, urgency, summary) on each email card
3. **User clicks an email** → Full content is fetched from Zoho, and AI analysis runs if not cached
4. **Analysis results** appear in the reading pane with summary, key points, and a suggested reply
5. **All results** are saved to Firestore for fast future access and dashboard analytics

## API Endpoints

| Route | Method | Description |
|---|---|---|
| `/` | GET | Mail client UI |
| `/dashboard` | GET | Analytics dashboard |
| `/api/inbox` | GET | Fetch inbox with cached AI data |
| `/api/folders` | GET | List Zoho Mail folders |
| `/api/email/<id>` | GET | Full email + analysis (triggers analysis if needed) |
| `/api/analyze/<id>` | POST | Force re-analysis |
| `/api/history` | GET | Analysis history from Firestore |
| `/api/stats` | GET | Aggregated dashboard statistics |

## Setup

1. **Clone and install:**
   ```bash
   git clone <repository-url>
   cd smartmail-main-gmail
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create a `.env` file:**
   ```
   # Zoho Mail API
   ZOHO_CLIENT_ID=...
   ZOHO_CLIENT_SECRET=...
   ZOHO_REFRESH_TOKEN=...
   ZOHO_ACCOUNT_ID=...          # Optional, auto-detected

   # Firebase Admin SDK
   FIREBASE_TYPE=service_account
   FIREBASE_PROJECT_ID=...
   FIREBASE_PRIVATE_KEY_ID=...
   FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   FIREBASE_CLIENT_EMAIL=...
   FIREBASE_CLIENT_ID=...
   FIREBASE_AUTH_URI=...
   FIREBASE_TOKEN_URI=...
   FIREBASE_AUTH_PROVIDER_CERT_URL=...
   FIREBASE_CLIENT_CERT_URL=...

   # OpenRouter API
   OPENROUTER_API_KEY=...
   OPENROUTER_REFERER_URL=https://your-app-url.com
   ```

3. **Run locally:**
   ```bash
   python app.py
   ```
   Open `http://localhost:5000` for the mail client, `http://localhost:5000/dashboard` for analytics.

## Deployment

Configured for Render, Heroku, or any platform supporting Python/Gunicorn:

```
web: gunicorn app:app
```

## Key Dependencies

- **Flask** — Web framework
- **Requests** — HTTP client for Zoho & OpenRouter APIs
- **firebase-admin** — Firestore integration
- **beautifulsoup4** — HTML email content cleaning
- **gunicorn** — Production WSGI server
- **python-dotenv** — Environment variable management
