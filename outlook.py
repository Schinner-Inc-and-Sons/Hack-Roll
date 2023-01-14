'''
1. Get access token
2. Get emails


https://github.com/Azure-Samples/ms-identity-python-devicecodeflow/blob/master/device_flow_sample.py
'''

import sys
import msal
import json
import requests

OUTLOOK_HOST = 'outlook.office365.com'
GMAIL_HOST = 'imap.gmail.com'
IMAP_PORT = 993


def generate_auth_string(user, token):
    return 'user=%s\1auth=Bearer %s\1\1' % (user, token)


client_id = '71ed423c-835c-4ed1-bb1d-a2e7c1cdab20'
authority = 'https://login.microsoftonline.com/common'
scope = [
    'IMAP.AccessAsUser.All',
    'Mail.Read',
]
app = msal.PublicClientApplication(client_id=client_id, authority=authority)

result = None

accounts = app.get_accounts()
if accounts:
    print('Pick account:')
    for a in accounts:
        print(a['username'])
    index = int(input('index: '))
    chosen = accounts[index]
    result = app.acquire_token_silent(scope, account=chosen)

if not result:
    print('Initiating device flow')
    flow = app.initiate_device_flow(scopes=scope)
    if 'user_code' not in flow:
        raise ValueError('Failed to create device flow: ', json.dumps(flow))
    print('Acquiring token')
    print(flow['message'])
    sys.stdout.flush()
    result = app.acquire_token_by_device_flow(flow)

access_token = result['access_token']
client = result['id_token_claims']
name = client['name']
username = client['preferred_username']
print('Token acquired for', name, username)

"""
https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview?view=graph-rest-1.0
"""


r = requests.get(
    'https://graph.microsoft.com/v1.0/me/messages',
    headers=dict(Authorization=access_token))

data = json.loads(r.text)
data = data['value']

for d in data:
    if not 'from' in d:
        continue
    if not 'subject' in d:
        continue
    print('From:', d['from']['emailAddress']['address'])
    print('Subject:', d['subject'])
    print()

with open('output.txt', 'w+') as f:
    f.write(r.text)
