# VectorShift Integrations Technical Assessment

## Overview
This project implements OAuth integrations with HubSpot, Airtable, and Notion using FastAPI backend and React frontend. The main focus is on implementing the HubSpot OAuth flow and data retrieval.

## Project Structure
```
/
├── frontend/
│   └── src/
│       └── integrations/
│           ├── airtable.js
│           ├── notion.js
│           └── hubspot.js
└── backend/
    └── integrations/
        ├── airtable.py
        ├── notion.py
        └── hubspot.py
```

## Setup Instructions

### Environment Variables
Create a `.env` file in the `/backend` directory:

```bash
CLIENT_ID="your_hubspot_client_id"
CLIENT_SECRET="your_hubspot_client_secret"
REDIS_HOST="your_redis_host"
REDIS_PASSWORD="your_redis_password"
```

### Redis Configuration
- Redis is used for state management in the OAuth flow
- The project uses Upstash (https://upstash.com/) for Redis hosting
- TLS/SSL encryption is configured by default
- States are stored with key format: `hubspot_state_{org_id}_{user_id}`

### HubSpot App Configuration
1. Create a new HubSpot app with:
   - App name, description, and logo
   - Configure OAuth settings in Auth tab
   - Set Redirect URI and required scopes
   - Register Callback URL
2. Get `CLIENT_ID` and `CLIENT_SECRET` from app settings
3. Create a Developer Test Account for testing

## Running the Application

### Frontend
```bash
cd frontend
npm install
npm start
```

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## OAuth Flow Implementation
1. The authorization URL includes a CSRF-safe state parameter
2. State is stored in Redis for validation
3. HubSpot redirects to `/integrations/hubspot/oauth2callback`
4. Callback handler:
   - Validates `code` parameter
   - Verifies state against Redis
   - Exchanges code for access/refresh tokens
   - Stores credentials in KV store

## Data Retrieval
- After authentication, the system fetches contacts from HubSpot
- Contact data is serialized to `IntegrationItem` format
- Results can be viewed in console output


## Security Considerations
- CSRF protection implemented via state parameter
- Secure credential storage in KV store
- TLS/SSL encryption for Redis communication