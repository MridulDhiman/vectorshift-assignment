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
from datetime import datetime
from dateutil import parser
from typing import Optional, List 

load_dotenv()

CLIENT_ID=os.getenv("CLIENT_ID");
CLIENT_SECRET = os.getenv("CLIENT_SECRET");
REDIRECT_URI = 'http%3A%2F%2Flocalhost%3A8000%2Fintegrations%2Fhubspot%2Foauth2callback'
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=oauth%20crm.objects.contacts.read'
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
                    'redirect_uri': "http://localhost:8000/integrations/hubspot/oauth2callback",
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )
    print("response: ", response.json())
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

async def create_integration_item_metadata_object(contact):
    """Transform HubSpot contact data into IntegrationItem format"""
    properties = contact.get('properties', {})
    
    # Parse dates using dateutil.parser instead of datetime.fromisoformat
    try:
        creation_time = parser.parse(properties.get('createdate')) if properties.get('createdate') else None
        modified_time = parser.parse(properties.get('lastmodifieddate')) if properties.get('lastmodifieddate') else None
    except (ValueError, TypeError):
        creation_time = None
        modified_time = None
    
    return IntegrationItem(
        id=str(contact.get('id')),
        type='contact',
        directory=False,
        name=f"{properties.get('firstname', '')} {properties.get('lastname', '')}".strip(),
        creation_time=creation_time,
        last_modified_time=modified_time,
        url=f"https://app.hubspot.com/contacts/contacts/{contact.get('id')}",
        mime_type='application/hubspot.contact',
        visibility=True
    )

async def get_items_hubspot(credentials):
    """Fetch contacts from HubSpot and convert them to IntegrationItem objects"""
    if isinstance(credentials, str):
        credentials = json.loads(credentials)
    
    integration_items = []
    after = None
    
    while True:
        url = 'https://api.hubapi.com/crm/v3/objects/contacts'
        params = {
            'limit': 100,
            'properties': [
                'firstname',
                'lastname',
                'email',
                'phone',
                'company',
                'createdate',
                'lastmodifieddate'
            ],
            'archived': False
        }
        
        if after:
            params['after'] = after
            
        try:
            response = requests.get(
                url,
                headers={
                    'Authorization': f'Bearer {credentials.get("access_token")}',
                    'Content-Type': 'application/json',
                },
                params=params
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Process results
            results = data.get('results', [])
            for contact in results:
                integration_item = await create_integration_item_metadata_object(contact)
                integration_items.append(integration_item)
            
            # Check for pagination
            paging = data.get('paging', {})
            if not paging.get('next'):
                break
                
            after = paging.get('next').get('after')
            
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=response.status_code if response else 500,
                detail=f"Error fetching HubSpot contacts: {str(e)}"
            )
    print("integration_items: ", integration_items)
    return json.dumps(integration_items)

