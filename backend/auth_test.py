import os
from google_auth_oauthlib.flow import InstalledAppFlow

# The permission we need (saving files to Drive)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

print("🚀 Starting Google Authentication...")
try:
    # This specifically looks for the file you have in your sidebar
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    
    # This forces the browser to open!
    creds = flow.run_local_server(port=0)
    
    # Once you click "Allow" in the browser, it saves the token
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
        
    print("✅ SUCCESS! token.json has been created! You can close this terminal.")
except Exception as e:
    print(f"❌ ERROR: {e}")