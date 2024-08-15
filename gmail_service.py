import os  # Módulo para interactuar con el sistema operativo, como verificar la existencia de archivos
import pickle  # Módulo para serializar y deserializar objetos de Python
import base64  # Módulo para codificar y decodificar datos en base64
from googleapiclient.discovery import build  # Función para construir un cliente de API de Google
from google.auth.transport.requests import Request  # Clase para manejar solicitudes de autenticación
from google.oauth2.credentials import Credentials  # Clase para manejar credenciales OAuth2
from google_auth_oauthlib.flow import InstalledAppFlow  # Clase para manejar el flujo de autenticación de OAuth2
from bs4 import BeautifulSoup  # Librería para analizar y manipular documentos HTML y XML

# Definir el alcance (scope) de la aplicación, es decir, el nivel de acceso a la API de Gmail.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """
    Autentica al usuario en la API de Gmail y devuelve un objeto de servicio que puede ser utilizado para realizar
    llamadas a la API.
    """
    creds = None
    # Verificar si el archivo de token existe, el cual almacena las credenciales del usuario
    if os.path.exists('token.pickle'):
        # Cargar las credenciales desde el archivo
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Si no hay credenciales válidas, iniciar el proceso de autenticación
    if not creds or not creds.valid:
        # Si las credenciales existen pero están expiradas, se intenta refrescar
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Si no hay credenciales, se inicia el flujo de autenticación para obtener nuevas credenciales
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardar las credenciales para el próximo uso
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    # Construir el objeto de servicio de Gmail utilizando las credenciales autenticadas
    service = build('gmail', 'v1', credentials=creds)
    return service

def extract_parts(parts, email_data):
    """
    Extrae las partes del cuerpo del correo electrónico (texto y HTML) y las guarda en un diccionario.
    """
    for part in parts:
        mime_type = part['mimeType']  # Obtener el tipo MIME de la parte del correo (texto plano o HTML)
        body_data = part['body'].get('data')  # Obtener los datos codificados en base64
        # Si la parte contiene otras subpartes, se llama recursivamente a la función para extraerlas
        if 'parts' in part:
            extract_parts(part['parts'], email_data)
        # Si los datos están presentes, se decodifican y se almacenan en el diccionario
        elif body_data:
            decoded_data = base64.urlsafe_b64decode(body_data).decode('utf-8')
            if mime_type == 'text/plain':  # Si es texto plano, se almacena como 'content'
                email_data['content'] = decoded_data
            elif mime_type == 'text/html':  # Si es HTML, se almacena como 'content_html'
                email_data['content_html'] = decoded_data

def get_latest_email(service, query):
    """
    Obtiene el correo electrónico más reciente que coincide con la consulta dada.
    """
    # Realiza una solicitud para listar los mensajes que coinciden con la consulta, limitando los resultados a 1
    results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
    messages = results.get('messages', [])
    
    # Si no se encuentran mensajes, retorna None
    if not messages:
        return None
    
    # Obtiene el ID del mensaje más reciente y luego lo recupera usando el ID
    msg = messages[0]
    msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
    payload = msg_data['payload']  # El payload contiene la información principal del correo
    headers = payload['headers']  # Los headers incluyen información como el asunto y la fecha
    
    # Inicia el diccionario para almacenar los datos del correo
    email_data = {'id': msg['id']}
    # Extrae el asunto y la fecha del correo desde los headers
    for header in headers:
        if header['name'] == 'Subject':
            email_data['subject'] = header['value']
        if header['name'] == 'Date':
            email_data['date'] = header['value']
    
    # Si el payload tiene partes, se extraen usando la función extract_parts
    parts = payload.get('parts', [])
    if parts:
        extract_parts(parts, email_data)
        # Si el correo tiene contenido HTML, se limpia el HTML y se extrae el texto limpio
        if 'content_html' in email_data:
            soup = BeautifulSoup(email_data['content_html'], 'html.parser')
            email_data['clean_content'] = soup.get_text(separator="\n", strip=True)
    
    # Devuelve el diccionario con los datos del correo
    return email_data