from flask import Blueprint, request, jsonify
from database import get_connection
import secrets
import re
from utils import registrar_log

bp = Blueprint("instituicoes", __name__)

@bp.route("/registrar-instituicao", methods=["POST"])
def registrar_instituicao():
    data = request.json
    nome = data.get("nome_fantasia")
    cnpj = data.get("cnpj")

    # Validação de campos obrigatórios
    if not nome or not cnpj:
        return jsonify({"erro": "Campos 'nome_fantasia' e 'cnpj' são obrigatórios."}), 400

    # Validação básica de CNPJ: apenas números e 14 dígitos
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    if len(cnpj_limpo) != 14:
        return jsonify({"erro": "CNPJ deve conter 14 dígitos numéricos."}), 400

    # Geração de token de acesso exclusivo para a instituição
    token = secrets.token_hex(16)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Inserção da nova instituição no banco
        cursor.execute("""
            INSERT INTO instituicoes (nome_fantasia, cnpj, token_acesso)
            VALUES (?, ?, ?)
        """, (nome, cnpj_limpo, token))
        conn.commit()

        # Registro de log da criação
        registrar_log(
            "registro_instituicao",
            cnpj_limpo,
            f"Instituição '{nome}' registrada com token {token}"
        )

        return jsonify({
            "mensagem": "Instituição registrada com sucesso.",
            "token_acesso": token
        }), 201

    except Exception as e:
        # Tratamento de erros de integridade e duplicidade
        if "UNIQUE constraint failed: instituicoes.cnpj" in str(e):
            return jsonify({"erro": "CNPJ já cadastrado."}), 409
        if "UNIQUE constraint failed: instituicoes.token_acesso" in str(e):
            return jsonify({"erro": "Erro interno: token duplicado. Tente novamente."}), 500
        return jsonify({"erro": str(e)}), 500

    finally:
        conn.close()
