# routes/boletos.py (adaptado)

from flask import Blueprint, request, jsonify
from database import get_connection
import uuid
from utils import registrar_log

bp = Blueprint("boletos", __name__)

@bp.route("/registrar-boleto", methods=["POST"])
def registrar_boleto():
    # Validação do token de acesso (Bearer)
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return jsonify({"erro": "Token de acesso ausente ou malformado. Use 'Bearer <token>'"}), 401

    token = token.split(" ")[1]
    conn = get_connection()
    cursor = conn.cursor()

    # Verifica se o token pertence a alguma instituição
    cursor.execute("SELECT id FROM instituicoes WHERE token_acesso = ?", (token,))
    instituicao = cursor.fetchone()

    if not instituicao:
        conn.close()
        return jsonify({"erro": "Token inválido. Acesso negado."}), 403

    # Leitura dos dados do boleto
    data = request.json
    codigo_barras = data.get("codigo_barras")
    data_vencimento = data.get("data_vencimento")
    valor = data.get("valor")
    beneficiario_nome = data.get("beneficiario_nome")
    beneficiario_cnpj = data.get("beneficiario_cnpj")
    status = data.get("status", "pendente")
    pagador_cad_cpf_cnpj = data.get("pagador_cad_cpf_cnpj")
    pagador_cad_nome = data.get("pagador_cad_nome")

    # Campos opcionais preenchidos apenas em casos suspeitos
    pagador_cpf_cnpj = data.get("pagador_cpf_cnpj") or None
    pagador_nome = data.get("pagador_nome") or None

    # Validação dos campos obrigatórios
    if not all([codigo_barras, data_vencimento, valor, pagador_cad_cpf_cnpj, pagador_cad_nome, beneficiario_nome, beneficiario_cnpj]):
        return jsonify({"erro": "Campos obrigatórios: codigo_barras, data_vencimento, valor, pagador_cad_cpf_cnpj, pagador_cad_nome, beneficiario_nome, beneficiario_cnpj"}), 400

    boleto_id = str(uuid.uuid4())
    recuperado_de_suspeita = False
    data_pagamento = None

    try:
        # Verifica se o boleto já foi registrado anteriormente como tentativa suspeita
        cursor.execute("SELECT * FROM tentativas_suspeitas WHERE codigo_barras = ?", (codigo_barras,))
        suspeita = cursor.fetchone()

        if suspeita:
            # Recupera os dados da tentativa suspeita e marca como pago
            status = "pago"
            data_pagamento = suspeita["data_verificacao"]
            pagador_cpf_cnpj = suspeita["pagador_cpf_cnpj"]
            pagador_nome = suspeita["pagador_nome"]

            # Remove os registros suspeitos relacionados
            cursor.execute("DELETE FROM tentativas_suspeitas WHERE codigo_barras = ?", (codigo_barras,))
            cursor.execute("DELETE FROM blacklist WHERE codigo_barras = ?", (codigo_barras,))
            recuperado_de_suspeita = True

        # Insere o boleto no banco com os dados consolidados
        cursor.execute("""
            INSERT INTO boletos 
            (id, codigo_barras, data_vencimento, valor, status, 
            pagador_cpf_cnpj, pagador_nome,
            pagador_cad_cpf_cnpj, pagador_cad_nome, 
            beneficiario_nome, beneficiario_cnpj, 
            id_instituicao, data_pagamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            boleto_id, codigo_barras, data_vencimento, valor, status,
            pagador_cpf_cnpj, pagador_nome,
            pagador_cad_cpf_cnpj, pagador_cad_nome,
            beneficiario_nome, beneficiario_cnpj,
            instituicao["id"], data_pagamento
        ))

        conn.commit()

        # Registro de log de criação
        registrar_log(
            "registro_boleto",
            token,
            f"Boleto {codigo_barras} registrado com status '{status}' (valor: R${valor}, vencimento: {data_vencimento}, pagador real: {pagador_cpf_cnpj})"
        )

        mensagem = "Boleto registrado com sucesso."
        if recuperado_de_suspeita:
            mensagem += " Boleto recuperado de tentativa suspeita. Dados de pagador foram anexados."

        return jsonify({
            "mensagem": mensagem,
            "id_boleto": boleto_id
        }), 201

    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    finally:
        conn.close()
