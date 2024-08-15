from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from llm_processing import send_message, gastos_mes
from gmail_service import authenticate_gmail, get_latest_email

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.route('/')
def index():
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    return render_template('index.html', conversation=session['conversation_history'], gastos=gastos_mes)

@app.route('/check-email', methods=['POST'])
def check_email():
    query = request.form.get('query')
    
    service = authenticate_gmail()
    latest_email = get_latest_email(service, query)
    
    if latest_email:
        clean_content = latest_email.get('clean_content', latest_email.get('content', ''))
        llm_response = send_message(clean_content)
        session['conversation_history'].append({'sender': 'email', 'message': clean_content})
        session['conversation_history'].append({'sender': 'llm', 'message': llm_response})
    else:
        llm_response = "No new emails found."
        session['conversation_history'].append({'sender': 'llm', 'message': llm_response})
    
    session.modified = True
    return jsonify({
        'conversation': session['conversation_history'],
        'gastos': gastos_mes
    })

@app.route('/respond-llm', methods=['POST'])
def respond_llm():
    user_response = request.form.get('llm_response')
    final_message = send_message(user_response, is_user_response=True)
    
    session['conversation_history'].append({'sender': 'user', 'message': user_response})
    session['conversation_history'].append({'sender': 'llm', 'message': final_message})
    
    session.modified = True
    return jsonify({
        'conversation': session['conversation_history'],
        'gastos': gastos_mes
    })

if __name__ == '__main__':
    app.run(debug=True)