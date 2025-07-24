import os
import io
import csv
from email.utils import formataddr

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
from flask import Flask
from config import Config
from flask_migrate import Migrate


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- Configuração Inteligente do Banco de Dados ---
db_uri = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')

# Se nenhuma variável de produção for encontrada, usa o SQLite local.
if not db_uri:
    db_path = os.path.join(os.path.dirname(__file__), 'trash/local.db')
    db_uri = 'sqlite:///{}'.format(db_path)
    print("AVISO: Usando banco de dados SQLite local para desenvolvimento.")

# Corrige o prefixo para o PostgreSQL (necessário para o SQLAlchemy)
elif db_uri.startswith("postgres://"):
    db_uri = db_uri.replace("postgres://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- NOVA CONFIGURAÇÃO DE E-MAIL ---
# --- Configuração do Email ---
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'super.dadosbr@gmail.com'
MAIL_PASSWORD = 'wcjt grmi vrnq vuno'
MAIL_DEFAULT_SENDER = MAIL_USERNAME

mail = Mail(app)  # Inicializa o Flask-Mail


# --- Modelo do Banco de Dados (sem alteração) ---
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    grau_instrucao = db.Column(db.String(50), nullable=True)  # NOVO
    mensagem = db.Column(db.Text, nullable=True)
    origem = db.Column(db.String(100), nullable=True)  # NOVO: evento/campanha
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)  # NOVO


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
        #interesse = request.form.get('interesse')
        mensagem = request.form.get('mensagem')

        if not Lead.query.filter_by(email=email).first():
            novo_lead = Lead(nome=nome, email=email, whatsapp=whatsapp, rating=rating, mensagem=mensagem)
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
    - Mensagem: {lead.mensagem}

    Acesse a lista completa em seu painel.
    """
    msg = Message(assunto, recipients=[destinatario], body=corpo)
    mail.send(msg)
    print(f"E-mail de notificação enviado para {destinatario}")


@app.route("/programas")
def programas():
    return redirect("/ia-edu")
@app.route("/ia-edu")
def ia_edu():
    return render_template("mentoria_iaedu.html")

# --- NOVAS ROTAS DE ADMIN ---

@app.route('/upload-csv', methods=['GET', 'POST'])
def upload_csv():
    if request.method == 'POST':
        file = request.files['file']
        origem = request.form.get('origem', 'Importação Manual')

        if not file:
            return "Nenhum arquivo enviado.", 400

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        next(csv_input)  # Pula o cabeçalho

        for row in csv_input:
            nome, email, whatsapp, rating, grau_instrucao, mensagem = row

            if not Lead.query.filter_by(email=email).first():
                lead = Lead(
                    nome=nome,
                    email=email,
                    whatsapp=whatsapp,
                    rating=int(rating),
                    grau_instrucao=grau_instrucao,
                    mensagem=mensagem,
                    origem=origem
                )
                db.session.add(lead)
        db.session.commit()

        return redirect(url_for('inscricoes'))

    return render_template('upload_csv.html')

    # Formato CSV: nome,email,whatsapp,rating,grau_instrucao,mensagem



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

@app.route('/enviar-brinde', methods=['GET'])
def enviar_brinde():
    leads = Lead.query.order_by(Lead.id.desc()).all()
    return render_template('enviar_brinde.html', leads=leads)

@app.route('/preview-brinde', methods=['POST'])
def preview_brinde():
    link_brinde = request.form.get('link_brinde')
    mensagem_base = request.form.get('mensagem_base')
    lead_ids = request.form.getlist('lead_ids')

    leads = Lead.query.filter(Lead.id.in_(lead_ids)).all()

    return render_template('preview_brinde.html', leads=leads, link_brinde=link_brinde, mensagem_base=mensagem_base)

@app.route('/confirmar-envio-brinde', methods=['POST'])
def confirmar_envio_brinde():
    selected_ids = request.form.getlist('selected_leads')
    link_brinde = request.form.get('link_brinde')

    if not selected_ids:
        flash('Nenhum inscrito selecionado.', 'warning')
        return redirect(url_for('enviar_brinde'))

    leads = Lead.query.filter(Lead.id.in_(selected_ids)).all()

    for lead in leads:
        corpo_email = render_template('email_template2.html', lead=lead, link_brinde=link_brinde)
        msg = Message("🎁 Seu e-book chegou!!",
                      sender=formataddr(("Plataforma SD+", app.config['MAIL_USERNAME'])),
                      recipients=[lead.email],
                      html=corpo_email)
        mail.send(msg)

    #flash('Emails enviados com sucesso!', 'success')
    return redirect(url_for('inscricoes'))



@app.route('/formia', methods=['GET','POST'])
def form_ia():
    return render_template("form_redirect.html")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)