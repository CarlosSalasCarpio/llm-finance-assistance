from openai import OpenAI
import re
import ast

# LLM initialization
client = OpenAI()

role_system = "system"
role_user = "user"
role_assistant = "assistant"

content_system = (
    "Eres un asistente que se utilizará dentro de una app de finanzas personales. "
    "Recibirás el contenido de correos bancarios enviados al usuario. Tu objetivo es transformar esta información "
    "en un diccionario de Python para poder gestionar los datos con facilidad. Aquí tienes un ejemplo de un correo: \n"
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
    "El diccionario de Python debe incluir los siguientes campos: 'tarjeta', 'fecha', 'establecimiento', 'valor', 'hora', y 'categoría'. "
    "Propondrás una de las siguientes categorías básicas: alimentación, ocio, transporte, compras, salud, educación, cuidado personal, hogar y otros. "
    "Es importante que tú propongas una categoría al usuario, según el contenido. Por ejemplo, en la información mostrada, al ser el establecimiento "
    "una barbería (Barber Planet), propondrás la categoría cuidado personal. "
    "Preguntarás al usuario si está de acuerdo con la categoría asignada. Si el usuario confirma, devolverás el diccionario definitivo. "
    "Es de vital importancia que repuesta tenga simpere la siguiente estructura 'Perfecto, el gasto ha sido registrado con éxito [y aqui el diccionario]'"
    "La estructura de tu respuesta deberá contener la descripción de la transacción, la categoría propuesta y, explícitamente, "
    "preguntar al usuario si está de acuerdo o no con la categoría. "
    "Esto puede ser del estilo: 'Tienes una nueva transacción por un valor de $90,000.00 en Barber Planet. Esto parece pertenecer "
    "a la categoría cuidado personal. ¿Estás de acuerdo con que registre este gasto?'"
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
    
    # Hacer la solicitud a la API con todo el historial
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    
    # Obtener la respuesta del asistente
    assistant_message = completion.choices[0].message.content
    
    # Agregar la respuesta del asistente al historial
    messages.append({"role": "assistant", "content": assistant_message})
    
    # Buscar un diccionario en la respuesta del asistente
    dict_match = re.search(r'\{.*?\}', assistant_message, re.DOTALL)
    if dict_match:
        try:
            gasto_dict = ast.literal_eval(dict_match.group())
            gastos_mes.append(gasto_dict)
            print(f"Nuevo gasto registrado: {gasto_dict}")
            print(f"Total de gastos registrados: {len(gastos_mes)}")
        except:
            print("Error al procesar el diccionario")
    
    return assistant_message