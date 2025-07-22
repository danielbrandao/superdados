import os
import io
import csv
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message  # NOVO IMPORT

app = Flask(__name__)

# --- Configuração Inteligente do Banco de Dados ---
db_uri = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')

# Se nenhuma variável de produção for encontrada, usa o SQLite local.
if not db_uri:
    db_path = os.path.join(os.path.dirname(__file__), 'local.db')
    db_uri = 'sqlite:///{}'.format(db_path)
    print("AVISO: Usando banco de dados SQLite local para desenvolvimento.")

# Corrige o prefixo para o PostgreSQL (necessário para o SQLAlchemy)
elif db_uri.startswith("postgres://"):
    db_uri = db_uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- NOVA CONFIGURAÇÃO DE E-MAIL ---
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Seu email do Gmail
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Sua senha de app de 16 letras
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)  # Inicializa o Flask-Mail


# --- Modelo do Banco de Dados (sem alteração) ---
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    interesse = db.Column(db.String(50), nullable=False)
    mensagem = db.Column(db.Text, nullable=True)


with app.app_context():
    db.create_all()


# --- ROTAS ---

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/edu', methods=['GET', 'POST'])
def edu_form():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        whatsapp = request.form.get('whatsapp')
        rating = request.form.get('rating')
        interesse = request.form.get('interesse')
        mensagem = request.form.get('mensagem')

        if not Lead.query.filter_by(email=email).first():
            novo_lead = Lead(nome=nome, email=email, whatsapp=whatsapp, rating=rating, interesse=interesse,
                             mensagem=mensagem)
            try:
                db.session.add(novo_lead)
                db.session.commit()
                # ✅ NOVO: ENVIA O E-MAIL APÓS SALVAR
                try:
                    enviar_email_notificacao(novo_lead)
                except Exception as e:
                    print(f"ERRO AO ENVIAR E-MAIL: {e}")  # Loga o erro, mas não quebra a aplicação
            except Exception as e:
                print(f"Erro ao salvar no banco: {e}")
                db.session.rollback()
            finally:
                db.session.close()

        return redirect(url_for('obrigado'))

    return render_template('form.html')


@app.route('/obrigado')
def obrigado():
    return render_template('obrigado.html')


# --- NOVA FUNÇÃO PARA ENVIAR E-MAIL ---
def enviar_email_notificacao(lead):
    # O email será enviado para o mesmo endereço configurado para enviar
    destinatario = app.config['ADMIN_EMAIL']
    if not destinatario:
        print("AVISO: MAIL_USERNAME não configurado. E-mail de notificação não será enviado.")
        return

    assunto = f"Nova Inscrição Recebida: {lead.nome}"
    corpo = f"""
    Uma nova inscrição foi realizada no formulário.

    Detalhes:
    - Nome: {lead.nome}
    - Email: {lead.email}
    - WhatsApp: {lead.whatsapp}
    - Avaliação: {lead.rating} de 5 estrelas
    - Interesse: {lead.interesse}
    - Mensagem: {lead.mensagem}

    Acesse a lista completa em seu painel.
    """
    msg = Message(assunto, recipients=[destinatario], body=corpo)
    mail.send(msg)
    print(f"E-mail de notificação enviado para {destinatario}")


# --- NOVAS ROTAS DE ADMIN ---
@app.route('/inscricoes')
def inscricoes():
    todos_os_leads = Lead.query.order_by(Lead.id.desc()).all()
    return render_template('inscricoes.html', leads=todos_os_leads)


@app.route('/export/csv')
def export_csv():
    leads = Lead.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Nome', 'Email', 'WhatsApp', 'Avaliacao', 'Interesse', 'Mensagem'])
    for lead in leads:
        writer.writerow([lead.id, lead.nome, lead.email, lead.whatsapp, lead.rating, lead.interesse, lead.mensagem])
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=inscricoes.csv"
    response.headers["Content-type"] = "text/csv"
    return response


# --- Rotas Utilitárias (sem alteração) ---
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(debug=True)