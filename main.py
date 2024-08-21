from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from llm_processing import send_message  # Asegúrate de que llm_processing.py esté en el mismo directorio

# Función para manejar mensajes de texto y enviarlos al LLM
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    # Enviar el mensaje al LLM para su procesamiento
    llm_response = send_message(user_message, 'user')
    # Devolver la respuesta del LLM al usuario en Telegram
    await update.message.reply_text(llm_response)

if __name__ == "__main__":
    # Configura el bot con tu token
    application = Application.builder().token("7100014049:AAEeN99I6-oRZisfo4otQ77-HpJyQ8wG_rc").build()

    # Añadir manejador para mensajes de texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Ejecutar el bot
    application.run_polling()