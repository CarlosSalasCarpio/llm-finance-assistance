import sqlite3
from openai import OpenAI
import re

# Inicializar la conexión a SQLite
conn = sqlite3.connect('gastos.db')
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute('''
CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tarjeta TEXT,
    fecha TEXT,
    establecimiento TEXT,
    valor REAL,
    hora TEXT,
    categoria TEXT
)
''')
conn.commit()

# Inicializar el LLM
client = OpenAI()

role_system = "system"
role_user = "user"
role_assistant = "assistant"

content_system = '''
Tu objetivo: Eres un asistente dentro de una app de finanzas personales. 
Recibirás el contenido de correos bancarios enviados al usuario. Tu objetivo es transformar esta información 
en un formato con emojis para poder gestionar los datos con facilidad.

Aquí tienes un ejemplo de un correo:

En BBVA nos transformamos para poner en tus manos todas las oportunidades del mundo. A continuación encuentras el 
comprobante de la transacción que realizaste.

Detalles de la operación:
Tarjeta terminada en: *4320
Fecha de la operación: 2024-07-27
Establecimiento: Barber Planet
Valor: $90,000.00
Hora: 19:14

Cada vez que recibas información de un correo nuevo, deberás responder al usuario con la siguiente estructura:

'Tienes una nueva transacción por un valor de $[valor] en [establecimiento]. Esto parece pertenecer 
a la categoría [aquí propondrás la categoría que consideres más adecuada]. ¿Estás de acuerdo con que registre este gasto en esta categoría?'

Debes proponer al usuario una de las siguientes categorías básicas. Debes ser estricto con las categorías; está prohibido utilizar categorías que no estén listadas a continuación:

- alimentación
- ocio
- transporte
- compras
- salud
- educación
- cuidado personal
- otros 

Es importante que propongas una categoría al usuario según el contenido. Por ejemplo, en el correo de ejemplo, al ser el 
establecimiento una barbería (Barber Planet), propondrás la categoría cuidado personal. 
Por lo tanto, preguntarás al usuario si está de acuerdo con la categoría asignada. 

Si el usuario está de acuerdo con la categoría (esto puede ser que el usuario responda con un simple 'sí', 'ok', 'adelante', 'yes', 
'sí, estoy de acuerdo' o cualquier otro tipo de respuesta afirmativa), tu siguiente respuesta debe tener la siguiente estructura: 
'Perfecto, el gasto ha sido registrado con éxito [y aquí la data estructurada]'. 
La data estructurada tendrá este formato:

💳 Tarjeta: [número de tarjeta]
📅 Fecha: [YYYY-MM-DD]  # Formato para la fecha
🏢 Establecimiento: [nombre del establecimiento]
💰 Valor: [monto de la transacción en formato $xx,xxx.xx]
🕒 Hora: [HH:MM o '-' si no está disponible]  # Formato para la hora
📂 Categoría: [categoría propuesta]

El usuario también puede proponer una categoría alternativa a la tuya; en ese caso, tu respuesta será la misma, pero con la categoría indicada por el usuario.

El usuario puede negarse a registrar el gasto, en cuyo caso simplemente responderás de forma amable y no generarás la estructura del gasto.

Ya que esta data será registrada en una BD, es importante que mantengas la estructura anterior al pie de la letra. 
Si algún campo viene vacío, como la fecha o la hora, igual pon el campo correspondiente; por ejemplo, si la hora viene vacía, pon '-'.

Recuerda que eres un asistente, utiliza el sentido común si una respuesta del usuario no está definida aquí. Puedes intentar guiarlo 
y pedir información adicional si es necesario. Puedes recordarle al usuario las categorías válidas si es conveniente. Mantén una conversación 
lo más humana y fluida posible para que el registro de data sea sencillo. Solo mantente estricto con la estructura de emojis y las categorías 
válidas. Fuera de eso, recuerda que eres un asistente amable y que quieres guiar al usuario para llevar el control de sus gastos de la 
mejor manera posible.

Si el usuario te hace preguntas sobre el estado actual de sus finanzas, deberás consultar su data directamente en la BD (en SQLite):

CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tarjeta TEXT,
    fecha TEXT,
    establecimiento TEXT,
    valor REAL,
    hora TEXT,
    categoria TEXT
)

Para esto, responderás con una consulta en SQL acorde a lo solicitado (ya la tabla está creada, generalmente un SELECT cumplirá con el
requerimiento). En este caso, debes responder únicamente con la consulta en SQL ya que tu respuesta será extraída utilizando regex
por un script en Python y ejecutada, si este es el caso, evita enviar cualquier texto
diferente a la consulta en SQL.

Cuando la data de la BD te sea retornada, darás una respuesta 
amable acorde que resuma su solicitud basándote en la data que recibas.

Por último, tu nombre es Janus!!!
'''

# Inicializar el historial de mensajes
messages = [
    {"role": role_system, "content": content_system}
]

def send_message(user_content, role):
    # Agregar el mensaje del usuario o del asistente al historial
    messages.append({"role": role, "content": user_content})
    
    print("\nHistorial de mensajes antes de la solicitud a la API:")
    for message in messages:
        print(f"{message['role']}: {message['content']}\n")
    
    # Hacer la solicitud a la API con todo el historial
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    
    # Obtener la respuesta del asistente
    assistant_message = completion.choices[0].message.content.strip()
    
    print("Mensaje del asistente:\n", assistant_message)
    
    # Añadir la respuesta del asistente al historial de mensajes
    messages.append({"role": role_assistant, "content": assistant_message})
    
    # Usar la nueva función para procesar la respuesta del LLM
    final_message = process_llm_response(assistant_message, cursor)
    
    # Retornar la respuesta final del LLM, ya sea la original o la generada tras la consulta SQL
    return final_message if final_message else assistant_message

def process_llm_response(assistant_message, cursor):
    lines = assistant_message.splitlines()
    gasto_dict = {}
    sql_query = None

    for line in lines:
        print(f"Procesando línea: {line}")  # Debugging: Imprimir cada línea que se procesa
        
        if "💳 Tarjeta:" in line:
            gasto_dict['tarjeta'] = line.split(":")[1].strip()
        elif "📅 Fecha:" in line:
            gasto_dict['fecha'] = line.split(":")[1].strip()
        elif "🏢 Establecimiento:" in line:
            gasto_dict['establecimiento'] = line.split(":")[1].strip()
        elif "💰 Valor:" in line:
            valor_texto = line.split(":")[1].strip()
            # Convertir el valor correctamente
            valor_numerico = re.sub(r'[^\d.]', '', valor_texto)  # Eliminar todo excepto dígitos y el punto decimal
            if valor_numerico:
                gasto_dict['valor'] = float(valor_numerico)
            else:
                gasto_dict['valor'] = 0  # Valor por defecto si no se encuentra valor numérico
        elif "🕒 Hora:" in line:
            hora_texto = line.split("🕒 Hora:")[1].strip()  # Asegurarse de que la hora completa se captura
            gasto_dict['hora'] = hora_texto if hora_texto != '-' else None
        elif "📂 Categoría:" in line:
            gasto_dict['categoria'] = line.split(":")[1].strip()
        elif "SELECT" in line.upper() or "INSERT" in line.upper() or "UPDATE" in line.upper() or "DELETE" in line.upper():
            # Si se detecta una consulta SQL en la línea, se asume que la línea completa es la consulta
            sql_query = line.strip()

    # Si se encontraron todos los campos de gasto, se añade al resultado y se guarda en la base de datos
    if all(key in gasto_dict for key in ['tarjeta', 'fecha', 'establecimiento', 'valor', 'categoria']):
        print(f"Nuevo gasto registrado: {gasto_dict}")

        try:
            cursor.execute('''
            INSERT INTO gastos (tarjeta, fecha, establecimiento, valor, hora, categoria)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (gasto_dict['tarjeta'], gasto_dict['fecha'], gasto_dict['establecimiento'], 
                  gasto_dict['valor'], gasto_dict['hora'], gasto_dict['categoria']))
            cursor.connection.commit()  # Commit the transaction
        except Exception as e:
            print("Error al guardar en la base de datos:", e)
    
    # Si se encontró una consulta SQL, se ejecuta y se vuelve a llamar a send_message con el resultado
    if sql_query:
        try:
            print(f"Ejecutando consulta SQL: {sql_query}")
            cursor.execute(sql_query)
            sql_result = cursor.fetchall()
            print(f"Resultado de la consulta SQL: {sql_result}")
            
            # Convertir el resultado a una cadena y enviar el mensaje de vuelta al LLM
            result_str = f"Resultado de la consulta SQL:\n{sql_result}"
            return send_message(result_str, 'system')
        except Exception as e:
            print("Error al ejecutar la consulta SQL:", e)

    # Si no hay consulta SQL, retornar None
    return None