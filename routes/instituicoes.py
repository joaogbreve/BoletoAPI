# Define as rotas para cadastro e autenticação de instituições (gera tokens e salva no banco).
from flask import Blueprint, request, jsonify       # Importa ferramentas do Flask
from database import get_connection                 # Função para conectar ao banco
import secrets                                      # Usado para gerar tokens seguros
import re                                           # Usado para limpar e validar o CNPJ
from utils import registrar_log                     # Função para registrar logs da ação

# Cria o blueprint para agrupar as rotas relacionadas às instituições
bp = Blueprint("instituicoes", __name__)

# Define a rota para registrar uma nova instituição
@bp.route("/registrar-instituicao", methods=["POST"])
def registrar_instituicao():
    # Lê os dados do JSON da requisição
    data = request.json
    nome = data.get("nome_fantasia")
    cnpj = data.get("cnpj")

    # Valida se os campos obrigatórios foram enviados
    if not nome or not cnpj:
        return jsonify({"erro": "Campos 'nome_fantasia' e 'cnpj' são obrigatórios."}), 400

    # Remove qualquer caractere não numérico do CNPJ
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    if len(cnpj_limpo) != 14:
        return jsonify({"erro": "CNPJ deve conter 14 dígitos numéricos."}), 400

    # Gera um token de acesso exclusivo de 32 caracteres hexadecimais (16 bytes)
    token = secrets.token_hex(16)

    # Conecta ao banco de dados
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Insere a instituição no banco com o token gerado
        cursor.execute("""
            INSERT INTO instituicoes (nome_fantasia, cnpj, token_acesso)
            VALUES (?, ?, ?)
        """, (nome, cnpj_limpo, token))
        conn.commit()

        # Registra log do evento
        registrar_log(
            "registro_instituicao",
            cnpj_limpo,
            f"Instituição '{nome}' registrada com token {token}"
        )

        # Retorna o token para o cliente
        return jsonify({
            "mensagem": "Instituição registrada com sucesso.",
            "token_acesso": token
        }), 201

    except Exception as e:
        # Tratamento específico para CNPJs duplicados (restrição UNIQUE)
        if "UNIQUE constraint failed: instituicoes.cnpj" in str(e):
            return jsonify({"erro": "CNPJ já cadastrado."}), 409

        # Caso raro: se o token gerado por acaso colidir com um existente
        if "UNIQUE constraint failed: instituicoes.token_acesso" in str(e):
            return jsonify({"erro": "Erro interno: token duplicado. Tente novamente."}), 500

        # Caso ocorra outro erro genérico
        return jsonify({"erro": str(e)}), 500

    finally:
        # Fecha a conexão com o banco em qualquer caso
        conn.close()

# Rota para listar todas as instituições cadastradas
@bp.route("/instituicoes", methods=["GET"])
def listar_instituicoes():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, nome_fantasia, cnpj, token_acesso FROM instituicoes")
        resultados = cursor.fetchall()

        instituicoes = []
        for linha in resultados:
            instituicoes.append({
                "id": linha[0],
                "nome_fantasia": linha[1],
                "cnpj": linha[2],
                "token_acesso": linha[3]
            })

        return jsonify(instituicoes), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    finally:
        conn.close()
