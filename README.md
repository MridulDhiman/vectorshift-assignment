## FastAPI Hubspot, Airtable, Notion OAuth Integration

### Steps and Workflow:

- Create New HubSpot App with name, description and logo.
- In the Auth tab, set the Redirect URI and scopes for the OAuth integration.
- Register the Callback URL for your application.
- Fetch the `CLIENT_ID` and `CLIENT_SECRET` after saving changes and save in `/backend/.env`

```bash
CLIENT_ID="XXX"
CLIENT_SECRET="XXX"
```

- Create Developer Test Account from the dashboard itself for allowing HubSpot to be used in your application.
- To prevent from CSRF attacks, we provide URL safe string to the state in the query parameters of the authorization URL, we can save that state either to session or redis. Here, we are using redis to manage json encoded hubspot state in the `hubspot_state_{org_id}_{user_id}` key.

- Redis server is running on upstash service, so start a new redis server on upstash and load the `REDIS_HOST` and `REDIS_PASSWORD` in the environment variables.

```bash
REDIS_HOST="localhost"
REDIS_PASSWORD="hawk_tuah"
```
- After successful OAuth authentication, Hubspot makes HTTP GET call to our `/integrations/hubspot/oauthcallback`. Here, we check if the request has `code` query parameter, otherwise return Bad Request status code. Verify the state returned against the encoded state in the redis to ensure valid authentication. 

