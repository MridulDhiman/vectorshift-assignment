# slack.py

import secrets 
import asyncio
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import json
import requests
from integrations.integration_item import IntegrationItem
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID=os.getenv("CLIENT_ID");
CLIENT_SECRET = os.getenv("CLIENT_SECRET");
REDIRECT_URI = 'http%3A%2F%2Flocalhost%3A8000%2Fintegrations%2Fhubspot%2Foauth2callback'
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=oauth%20crm.schemas.contacts.read'
token_uri= 'https://api.hubapi.com/oauth/v1/token'

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state' : secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', json.dumps(state_data), expire=600),
    
    return f"{authorization_url}&state={json.dumps(state_data)}"

async def oauth2callback_hubspot(request: Request): 
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(encoded_state)

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')
    
    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                token_uri,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': REDIRECT_URI,
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )
    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)
    
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

async def create_integration_item_metadata_object(response_json):
    print("response json: ", response_json)
    return {
        'id': response_json.get('vid'),
        'name': response_json.get('properties').get('firstname'),
        'email': response_json.get('properties').get('email'),
        'phone': response_json.get('properties').get('phone'),
        'company': response_json.get('properties').get('company'),
    }
    pass

async def get_items_hubspot(credentials):
    credentials = json.loads(credentials)
    response = requests.post(
        'https://api.hubapi.com/contacts/v1/lists/all/contacts/all',
        headers={
            'Authorization': f'Bearer {credentials.get("access_token")}',
            'Content-Type': 'application/json',
        },
    )
    print(response.json())
    if response.status_code == 200:
        results = response.json()['results']
        print(results)
        # list_of_integration_item_metadata = []
        # for result in results:
        #     list_of_integration_item_metadata.append(
        #         create_integration_item_metadata_object(result)
        #     )

        # print(list_of_integration_item_metadata)
    return
    pass