from serverless_http import handle
from meu_app import app  # importe sua aplicação Flask
handler = handle(app)  # empacota o app Flask