import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'mysecretkey')

    # --- Configuração do Banco de Dados ---
    db_uri = os.getenv('DATABASE_URL')
    if not db_uri:
        db_path = os.path.join(basedir, 'local.db')
        db_uri = 'sqlite:///{}'.format(db_path)
        print("AVISO: Usando banco de dados SQLite local para desenvolvimento.")
    elif db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql+psycopg2://", 1)

    SQLALCHEMY_DATABASE_URI = db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Configuração do Email ---
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'super.dadosbr@gmail.com'
    MAIL_PASSWORD = 'wcjt grmi vrnq vuno'
    MAIL_DEFAULT_SENDER = MAIL_USERNAME

