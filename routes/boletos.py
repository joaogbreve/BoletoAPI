# Importações necessárias
from flask import Blueprint, request, jsonify  # Flask para rotas e respostas JSON
from database import get_connection            # Função para conectar ao banco
import uuid                                    # Gera IDs únicos
from utils import registrar_log                # Função para registrar logs

# Criação do blueprint para organizar rotas relacionadas a boletos
bp = Blueprint("boletos", __name__)

# Define a rota que lida com o registro de boletos
@bp.route("/registrar-boleto", methods=["POST"])
def registrar_boleto():
    # Validação do token de acesso enviado no header Authorization
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return jsonify({"erro": "Token de acesso ausente ou malformado. Use 'Bearer <token>'"}), 401

    token = token.split(" ")[1] # Extrai apenas o token (remove o "Bearer")
    conn = get_connection()
    cursor = conn.cursor()

    # Verifica se o token pertence a alguma instituição
    cursor.execute("SELECT id FROM instituicoes WHERE token_acesso = ?", (token,))
    instituicao = cursor.fetchone()

    if not instituicao:
        conn.close()
        return jsonify({"erro": "Token inválido. Acesso negado."}), 403

    # Lê os dados do boleto enviados no corpo JSON da requisição
    data = request.json
    codigo_barras = data.get("codigo_barras")
    data_vencimento = data.get("data_vencimento")
    valor = data.get("valor")
    beneficiario_nome = data.get("beneficiario_nome")
    beneficiario_cnpj = data.get("beneficiario_cnpj")
    status = data.get("status", "pendente")
    pagador_cad_cpf_cnpj = data.get("pagador_cad_cpf_cnpj")
    pagador_cad_nome = data.get("pagador_cad_nome")

    # Campos opcionais (usados em casos suspeitos)
    pagador_cpf_cnpj = data.get("pagador_cpf_cnpj") or None
    pagador_nome = data.get("pagador_nome") or None

    # Verifica se os campos obrigatórios foram preenchidos
    if not all([codigo_barras, data_vencimento, valor, pagador_cad_cpf_cnpj, pagador_cad_nome, beneficiario_nome, beneficiario_cnpj]):
        return jsonify({"erro": "Campos obrigatórios: codigo_barras, data_vencimento, valor, pagador_cad_cpf_cnpj, pagador_cad_nome, beneficiario_nome, beneficiario_cnpj"}), 400

    # Gera um ID único para o boleto
    boleto_id = str(uuid.uuid4())
    recuperado_de_suspeita = False
    data_pagamento = None

    try:
        # Verifica se este boleto já havia sido registrado como tentativa suspeita
        cursor.execute("SELECT * FROM tentativas_suspeitas WHERE codigo_barras = ?", (codigo_barras,))
        suspeita = cursor.fetchone()

        if suspeita:
            # Se sim, considera o boleto como pago e recupera os dados suspeitos
            status = "pago"
            data_pagamento = suspeita["data_verificacao"]
            pagador_cpf_cnpj = suspeita["pagador_cpf_cnpj"]
            pagador_nome = suspeita["pagador_nome"]

            # Remove o registro das tabelas tentativas_suspeitas e blacklist
            cursor.execute("DELETE FROM tentativas_suspeitas WHERE codigo_barras = ?", (codigo_barras,))
            cursor.execute("DELETE FROM blacklist WHERE codigo_barras = ?", (codigo_barras,))
            recuperado_de_suspeita = True

        # Insere o boleto no banco
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
        conn.close() # Garante que a conexão com o banco será encerrada
        
@bp.route("/boletos", methods=["GET"])
def listar_boletos():
    # Validação do token de acesso no header Authorization
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return jsonify({"erro": "Token ausente ou malformado. Use 'Bearer <token>'"}), 401

    token = token.split(" ")[1]
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Verifica se o token é válido e obtém o ID da instituição
        cursor.execute("SELECT id FROM instituicoes WHERE token_acesso = ?", (token,))
        instituicao = cursor.fetchone()

        if not instituicao:
            return jsonify({"erro": "Token inválido. Acesso negado."}), 403

        # Busca os boletos da instituição
        cursor.execute("""
            SELECT id, codigo_barras, data_vencimento, valor, status,
                   pagador_cpf_cnpj, pagador_nome,
                   pagador_cad_cpf_cnpj, pagador_cad_nome,
                   beneficiario_nome, beneficiario_cnpj,
                   data_pagamento
            FROM boletos
            WHERE id_instituicao = ?
        """, (instituicao["id"],))
        
        resultados = cursor.fetchall()
        boletos = []

        for row in resultados:
            boletos.append({
                "id": row["id"],
                "codigo_barras": row["codigo_barras"],
                "data_vencimento": row["data_vencimento"],
                "valor": row["valor"],
                "status": row["status"],
                "pagador_cpf_cnpj": row["pagador_cpf_cnpj"],
                "pagador_nome": row["pagador_nome"],
                "pagador_cad_cpf_cnpj": row["pagador_cad_cpf_cnpj"],
                "pagador_cad_nome": row["pagador_cad_nome"],
                "beneficiario_nome": row["beneficiario_nome"],
                "beneficiario_cnpj": row["beneficiario_cnpj"],
                "data_pagamento": row["data_pagamento"]
            })

        return jsonify(boletos), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    finally:
        conn.close()
