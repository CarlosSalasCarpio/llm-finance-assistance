import os
import pickle
import base64
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import time

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Shows basic usage of the Gmail API."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    service = build('gmail', 'v1', credentials=creds)
    return service

def extract_parts(parts, email_data):
    for part in parts:
        mime_type = part['mimeType']
        body_data = part['body'].get('data')
        if 'parts' in part:
            extract_parts(part['parts'], email_data)  # Recursively extract parts
        elif body_data:
            decoded_data = base64.urlsafe_b64decode(body_data).decode('utf-8')
            if mime_type == 'text/plain':
                email_data['content'] = decoded_data
            elif mime_type == 'text/html':
                email_data['content_html'] = decoded_data

def get_latest_email(service, query):
    results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
    messages = results.get('messages', [])
    
    if not messages:
        return None
    
    msg = messages[0]
    msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
    payload = msg_data['payload']
    headers = payload['headers']
    
    email_data = {'id': msg['id']}
    for header in headers:
        if header['name'] == 'Subject':
            email_data['subject'] = header['value']
        if header['name'] == 'Date':
            email_data['date'] = header['value']
    
    parts = payload.get('parts', [])
    if parts:
        extract_parts(parts, email_data)
        if 'content_html' in email_data:
            soup = BeautifulSoup(email_data['content_html'], 'html.parser')
            email_data['clean_content'] = soup.get_text(separator="\n", strip=True)
    
    return email_data

def main():
    service = authenticate_gmail()
    
    # Query to find emails from the specific sender
    query = 'from:carlos.salas@hexagon.com'
    
    # Store the ID of the last seen message
    last_seen_id = None

    while True:
        latest_email = get_latest_email(service, query)
        
        if latest_email and latest_email['id'] != last_seen_id:
            last_seen_id = latest_email['id']
            print(f"Subject: {latest_email.get('subject')}")
            print(f"Date: {latest_email.get('date')}")
            print(f"Content: {latest_email.get('content', 'No text/plain content')}")
            print(f"Clean HTML Content: {latest_email.get('clean_content', 'No text/html content')}\n\n")
        
        # Wait for 10 seconds before checking again
        time.sleep(10)
        print('Reading inbox')

if __name__ == '__main__':
    main()
