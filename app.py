# app.py
from flask import Flask, render_template
from database import init_db
from routes.instituicoes import bp as instituicoes_bp
from routes.boletos import bp as boletos_bp
from routes.verificacao import bp as verificacao_bp
from routes.tentativa import bp as tentativas_bp

app = Flask(__name__)

# Inicializa o banco de dados, se necessário
init_db()

# Registra os blueprints (rotas organizadas por função)
app.register_blueprint(instituicoes_bp)
app.register_blueprint(boletos_bp)
app.register_blueprint(verificacao_bp)
app.register_blueprint(tentativas_bp)

# Rotas para as páginas web de demonstração
@app.route("/gerar-boleto")
def gerar_boleto():
    return render_template("gerar_boleto.html")

@app.route("/pagar-boleto")
def pagar_boleto():
    return render_template("pagar_boleto.html")

@app.route("/cadastrar-instituicao")
def cadastrar_instituicao():
    return render_template("cadastrar_instituicao.html")

if __name__ == "__main__":
    app.run(debug=True)
