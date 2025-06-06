from flask import Blueprint, request, jsonify
from database import get_connection
from difflib import SequenceMatcher
from utils import registrar_log
from datetime import datetime
import random
import string

bp = Blueprint("verificacao", __name__)

# Função para checar similaridade de nomes acima de 60%
def nomes_parecidos(nome1, nome2):
    return SequenceMatcher(None, nome1.lower(), nome2.lower()).ratio() > 0.6

# Geração aleatória de CPF ou CNPJ fake (para simulações)
def gerar_cpf_cnpj_aleatorio():
    tipo = random.choice([11, 14])
    return ''.join(random.choices(string.digits, k=tipo))

# Geração aleatória de nomes fakes (para simulações)
def gerar_nome_aleatorio():
    nomes = ["Carlos Silva", "Maria Souza", "João Pereira", "Ana Oliveira", "Pedro Lima", "Laura Costa"]
    return random.choice(nomes)

@bp.route("/verificar-boleto", methods=["POST"])
def verificar_boleto():
    data = request.json
    codigo_barras = data.get("codigo_barras")

    if not codigo_barras:
        return jsonify({"erro": "Campo obrigatório 'codigo_barras'."}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # Consulta o boleto na base
    cursor.execute("SELECT * FROM boletos WHERE codigo_barras = ?", (codigo_barras,))
    boleto = cursor.fetchone()

    if boleto:
        status = boleto["status"]

        # Check de blacklist por CNPJ do beneficiário ou CPF/CNPJ do pagador
        cursor.execute("""
            SELECT * FROM blacklist
            WHERE cnpj_benficiado = ? OR pagador_cad_cpf_cnpj = ?
        """, (boleto["beneficiario_cnpj"], boleto["pagador_cad_cpf_cnpj"]))
        registros = cursor.fetchall()

        beneficiario_blacklist = False
        pagador_blacklist = False
        motivos_beneficiario = set()
        motivos_pagador = set()

        for linha in registros:
            if linha["cnpj_benficiado"] == boleto["beneficiario_cnpj"]:
                beneficiario_blacklist = True
                motivos_beneficiario.add(linha["motivo"])
            if linha["pagador_cad_cpf_cnpj"] == boleto["pagador_cad_cpf_cnpj"]:
                pagador_blacklist = True
                motivos_pagador.add(linha["motivo"])

        # Se consta na blacklist, marca como suspeito
        if beneficiario_blacklist or pagador_blacklist:
            conn.close()
            return jsonify({
                "status": "suspeito",
                "mensagem": "Boleto ou pagador estão na blacklist.",
                "beneficiario_blacklist": beneficiario_blacklist,
                "pagador_blacklist": pagador_blacklist,
                "motivos_beneficiario": list(motivos_beneficiario),
                "motivos_pagador": list(motivos_pagador),
                "beneficiario_nome": boleto["beneficiario_nome"],
                "beneficiario_cnpj": boleto["beneficiario_cnpj"],
                "pagador_cad_cpf_cnpj": boleto["pagador_cad_cpf_cnpj"],
                "pagador_cad_nome": boleto["pagador_cad_nome"]
            })

        # Se já foi pago, status é "pago"
        if status == "pago":
            conn.close()
            return jsonify({
                "status": "pago",
                "mensagem": "Este boleto já foi pago.",
                "beneficiario_nome": boleto["beneficiario_nome"],
                "beneficiario_cnpj": boleto["beneficiario_cnpj"],
                "pagador_cad_cpf_cnpj": boleto["pagador_cad_cpf_cnpj"],
                "pagador_cad_nome": boleto["pagador_cad_nome"]
            })

        # Caso válido e limpo
        conn.close()
        registrar_log("verificacao_valida", boleto["beneficiario_cnpj"], f"Boleto {codigo_barras} validado com sucesso")
        return jsonify({
            "status": "valido",
            "mensagem": "Boleto encontrado e válido.",
            "beneficiario_nome": boleto["beneficiario_nome"],
            "beneficiario_cnpj": boleto["beneficiario_cnpj"],
            "pagador_cad_cpf_cnpj": boleto["pagador_cad_cpf_cnpj"],
            "pagador_cad_nome": boleto["pagador_cad_nome"]
        })

    # Caso não localizado, registra tentativa ignorada
    conn.close()
    registrar_log("verificacao_ignorada", "-", f"Boleto {codigo_barras} não encontrado.")
    return jsonify({
        "status": "ignorado",
        "mensagem": "Boleto não encontrado e não foi possível identificar a instituição."
    })


@bp.route("/pagar-boleto", methods=["POST"])
def pagar_boleto():
    data = request.json

    codigo_barras = data.get("codigo_barras")
    pagador_cpf_cnpj = data.get("pagador_cpf_cnpj")
    nome_pagador = data.get("nome_pagador")

    aceita_termos = data.get("aceita_termos", False)
    telefone = data.get("telefone", None)
    notificar_telefone = data.get("notificar_telefone", False)
    email = data.get("email", None)
    notificar_email = data.get("notificar_email", False)

    # Dados falsos para simulação de tentativas suspeitas
    cnpj_beneficiado_fake = data.get("cnpj_beneficiado_fake")
    nome_beneficiado_fake = data.get("nome_beneficiado_fake")
    pagador_cad_cpf_cnpj_fake = data.get("pagador_cad_cpf_cnpj_fake")
    pagador_cad_nome_fake = data.get("pagador_cad_nome_fake")

    if not all([codigo_barras, pagador_cpf_cnpj, nome_pagador]):
        return jsonify({"erro": "Campos obrigatórios: codigo_barras, pagador_cpf_cnpj, nome_pagador"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # Validação contra blacklist: código, beneficiário ou pagador
    cursor.execute("""
        SELECT * FROM blacklist
        WHERE codigo_barras = ? OR cnpj_benficiado = ? OR pagador_cad_cpf_cnpj = ?
    """, (codigo_barras, cnpj_beneficiado_fake, pagador_cpf_cnpj))
    registros = cursor.fetchall()

    bloqueio_beneficiario = False
    bloqueio_pagador = False
    motivos_beneficiario = set()
    motivos_pagador = set()

    for linha in registros:
        if linha["cnpj_benficiado"] == cnpj_beneficiado_fake:
            bloqueio_beneficiario = True
            motivos_beneficiario.add(linha["motivo"])
        if linha["pagador_cad_cpf_cnpj"] == pagador_cpf_cnpj:
            bloqueio_pagador = True
            motivos_pagador.add(linha["motivo"])

    # Se estiver na blacklist, bloqueia pagamento e informa
    if bloqueio_beneficiario or bloqueio_pagador:
        conn.close()
        return jsonify({
            "status": "suspeito",
            "mensagem": "Atenção: boleto ou pagador estão na blacklist.",
            "beneficiario_blacklist": bloqueio_beneficiario,
            "pagador_blacklist": bloqueio_pagador,
            "motivos_beneficiario": list(motivos_beneficiario),
            "motivos_pagador": list(motivos_pagador),
            "beneficiario_nome": nome_beneficiado_fake,
            "beneficiario_cnpj": cnpj_beneficiado_fake,
            "pagador_cad_cpf_cnpj": pagador_cpf_cnpj,
            "pagador_cad_nome": nome_pagador
        }), 200  # 200 para evitar erro no frontend

    # Verifica existência do boleto
    cursor.execute("SELECT * FROM boletos WHERE codigo_barras = ?", (codigo_barras,))
    boleto = cursor.fetchone()

    if boleto:
        divergencias = []

        # Validação dos dados do pagador
        if boleto["pagador_cad_cpf_cnpj"] != pagador_cpf_cnpj:
            divergencias.append("CPF/CNPJ do pagador divergente")
        if not nomes_parecidos(boleto["pagador_cad_nome"], nome_pagador):
            divergencias.append("Nome do pagador divergente")

        # Marca como pago com dados do pagador
        cursor.execute("""
            UPDATE boletos
            SET status = 'pago',
                data_pagamento = ?,
                pagador_cpf_cnpj = ?,
                pagador_nome = ?,
                aceita_termos = ?,
                telefone = ?,
                notificar_telefone = ?,
                email = ?,
                notificar_email = ?
            WHERE codigo_barras = ?
        """, (
            datetime.now(),
            pagador_cpf_cnpj,
            nome_pagador,
            aceita_termos,
            telefone,
            notificar_telefone,
            email,
            notificar_email,
            codigo_barras
        ))
        conn.commit()

        # Se houver divergência, registra tentativa suspeita
        if divergencias:
            cursor.execute("""
                INSERT INTO tentativas_suspeitas
                (codigo_barras, cnpj_benficiado, nome_benficiado,
                 pagador_cpf_cnpj, pagador_nome, pagador_cad_cpf_cnpj, pagador_cad_nome,
                 motivo, detalhes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                codigo_barras,
                boleto["beneficiario_cnpj"],
                boleto["beneficiario_nome"],
                pagador_cpf_cnpj,
                nome_pagador,
                boleto["pagador_cad_cpf_cnpj"],
                boleto["pagador_cad_nome"],
                "Divergências no pagamento",
                "; ".join(divergencias)
            ))
            conn.commit()

        conn.close()
        registrar_log("pagamento_boleto", codigo_barras, f"Boleto pago por {nome_pagador} ({pagador_cpf_cnpj}), divergências: {divergencias}")
        return jsonify({"sucesso": True, "divergencias": divergencias})

    # Se o boleto não existe, registra tentativa como suspeita
    cursor.execute("""
        INSERT INTO tentativas_suspeitas
        (codigo_barras, cnpj_benficiado, nome_benficiado,
         pagador_cpf_cnpj, pagador_nome, pagador_cad_cpf_cnpj, pagador_cad_nome,
         motivo, detalhes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        codigo_barras,
        cnpj_beneficiado_fake,
        nome_beneficiado_fake,
        pagador_cpf_cnpj,
        nome_pagador,
        pagador_cad_cpf_cnpj_fake,
        pagador_cad_nome_fake,
        "Boleto não encontrado, tentativa de pagamento suspeita",
        "Tentativa de pagamento com boleto inexistente"
    ))
    conn.commit()
    conn.close()

    registrar_log("pagamento_boleto_suspeito", codigo_barras, f"Tentativa de pagamento de boleto inexistente por {nome_pagador} ({pagador_cpf_cnpj})")
    return jsonify({"sucesso": True, "divergencias": ["Boleto não encontrado, pagamento registrado como suspeito"]})
