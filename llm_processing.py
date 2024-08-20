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

content_system = (
    "Eres un asistente que se utilizará dentro de una app de finanzas personales. "
    "Recibirás el contenido de correos bancarios enviados al usuario. Tu objetivo es transformar esta información "
    "en un formato con emojis para poder gestionar los datos con facilidad. Aquí tienes un ejemplo de un correo:\n"
    "\n"
    "En BBVA nos transformamos para poner en tus manos todas las oportunidades del mundo. A continuación encuentras el "
    "comprobante de la transacción que realizaste.\n"
    "\n"
    "Detalles de la operación:\n"
    "Tarjeta terminada en: *4320\n"
    "Fecha de la operación: 2024-07-27\n"
    "Establecimiento: Barber Planet\n"
    "Valor: $90,000.00\n"
    "Hora: 19:14\n"
    "\n" 
    "Cada vez que recibas un correo, en tu respuesta inicial propondrás al usuario una de las siguientes categorías básicas: alimentación, ocio, transporte, compras, salud, educación, "
    "cuidado personal, hogar y otros. "
    "Es importante que propongas una categoría al usuario según el contenido. Por ejemplo, en el correo de ejemplo, al ser el establecimiento "
    "una barbería (Barber Planet), propondrás la categoría cuidado personal. "
    "Por lo tanto, preguntarás al usuario si está de acuerdo con la categoría asignada."
    "Esto puede ser del estilo: 'Tienes una nueva transacción por un valor de $90,000.00 en Barber Planet. Esto parece pertenecer "
    "a la categoría cuidado personal. ¿Estás de acuerdo con que registre este gasto?'"
    "Si el usuario está de acuerdo con la categoría"
    "tu siguiente respuesta debe tener la siguiente estructura: 'Perfecto, el gasto ha sido registrado con éxito [y aquí la data estructurada]'."
    "La data estructurada tendrá este formato:\n"
    "💳 Tarjeta: [número de tarjeta]\n"
    "📅 Fecha: [YYYY-MM-DD]\n"  # Formato para la fecha
    "🏢 Establecimiento: [nombre del establecimiento]\n"
    "💰 Valor: [monto de la transacción en formato $xx,xxx.xx]\n"
    "🕒 Hora: [HH:MM o '-' si no está disponible]\n"  # Formato para la hora
    "📂 Categoría: [categoría propuesta]'.\n"
    "ya que esta data será registrada en un BD es importante que mantengas la estructura anterior al pie de la letra"
    "si algun campo viene vacío como la fecha o la hora, igual pon el campo correspondiente por ejemplo si la hora viene vacia pon '-'"
    "Tu nombre es Janus!!!"
)

# Inicializar el historial de mensajes
messages = [
    {"role": role_system, "content": content_system}
]

# Variable global para almacenar los gastos
gastos_mes = []

def send_message(user_content, is_user_response=False):
    global gastos_mes
    
    # Si es una respuesta del usuario, el rol es "user"
    role = role_user if is_user_response else role_assistant
    
    # Agregar el mensaje al historial
    messages.append({"role": role, "content": user_content})
    
    # Debugging: Imprimir el historial de mensajes
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
    
    # Debugging: Imprimir el mensaje del asistente
    print("Mensaje del asistente:\n", assistant_message)
    
    # Procesar el mensaje del asistente línea por línea
    lines = assistant_message.splitlines()
    gasto_dict = {}

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
            valor_numerico = re.findall(r'\d+\.?\d*', valor_texto)  # Extraer solo los números
            if valor_numerico:
                gasto_dict['valor'] = float(valor_numerico[0].replace(",", ""))  # Eliminar comas antes de convertir
            else:
                gasto_dict['valor'] = 0  # Default value si no se encuentra valor numérico
        elif "🕒 Hora:" in line:
            hora = line.split(":")[1].strip()
            gasto_dict['hora'] = hora if hora != '-' else None
        elif "📂 Categoría:" in line:
            gasto_dict['categoria'] = line.split(":")[1].strip()

    # Debugging: Imprimir el diccionario de gasto procesado
    print(f"Gasto procesado: {gasto_dict}")
    
    # Verificar si el diccionario contiene todos los campos
    if all(key in gasto_dict for key in ['tarjeta', 'fecha', 'establecimiento', 'valor', 'categoria']):
        gastos_mes.append(gasto_dict)
        print(f"Nuevo gasto registrado: {gasto_dict}")
        print(f"Total de gastos registrados: {len(gastos_mes)}")

        # Insertar en la base de datos
        try:
            cursor.execute('''
            INSERT INTO gastos (tarjeta, fecha, establecimiento, valor, hora, categoria)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (gasto_dict['tarjeta'], gasto_dict['fecha'], gasto_dict['establecimiento'], 
                  gasto_dict['valor'], gasto_dict['hora'], gasto_dict['categoria']))
            conn.commit()
        except Exception as e:
            print("Error al guardar en la base de datos:", e)
    else:
        print("Faltan datos en la estructura del gasto.")

    return assistant_message