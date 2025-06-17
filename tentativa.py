# Gerencia a listagem de tentativas suspeitas, incluindo a inserção e desbloqueio de boletos.
from flask import Blueprint, render_template, request, redirect, jsonify
from database import get_connection

# Criação do blueprint para o grupo de rotas relacionado a tentativas
bp = Blueprint("tentativas", __name__)

@bp.route("/tentativas-suspeitas", methods=["GET"])
def ver_tentativas():
    conn = get_connection()

    # Define que os resultados da query devem ser dicionários em vez de tuplas
    conn.row_factory = lambda cursor, row: {
        col[0]: row[idx] for idx, col in enumerate(cursor.description)
    }
    cursor = conn.cursor()

    # Recupera todas as tentativas suspeitas
    cursor.execute("SELECT * FROM tentativas_suspeitas ORDER BY data_verificacao DESC")
    tentativas = cursor.fetchall()

    # Recupera todos os códigos de barras já bloqueados na blacklist
    cursor.execute("SELECT codigo_barras FROM blacklist")
    codigos_bloqueados = {row["codigo_barras"] for row in cursor.fetchall()}

    conn.close()

    # Renderiza o HTML passando as tentativas e os códigos bloqueados
    return render_template("ver_tentativas_suspeitas.html", tentativas=tentativas, codigos_bloqueados=codigos_bloqueados)

@bp.route("/bloquear", methods=["POST"])
def bloquear_tentativa():
    tentativa_id = request.form.get("id")  # ID enviado via formulário
    conn = get_connection()
    cursor = conn.cursor()

    # Busca a tentativa pelo ID
    cursor.execute("SELECT * FROM tentativas_suspeitas WHERE id = ?", (tentativa_id,))
    tentativa = cursor.fetchone()

    if not tentativa:
        conn.close()
        return jsonify({"erro": "Tentativa não encontrada."}), 404

    # Verifica se já existe o mesmo codigo_barras na blacklist
    cursor.execute("SELECT * FROM blacklist WHERE codigo_barras = ?", (tentativa["codigo_barras"],))
    existe = cursor.fetchone()

    if existe:
        conn.close()
        return redirect("/blacklist")  # Ou poderia mostrar uma mensagem

    # Insere na blacklist com codigo_barras
    cursor.execute("""
        INSERT INTO blacklist (codigo_barras, nome, cnpj_benficiado, pagador_cad_cpf_cnpj, motivo)
        VALUES (?, ?, ?, ?, ?)
    """, (
        tentativa["codigo_barras"],
        tentativa["pagador_nome"],
        tentativa["cnpj_benficiado"],
        tentativa["pagador_cad_cpf_cnpj"],
        tentativa["motivo"]
    ))

    conn.commit()
    conn.close()

    return redirect("/tentativas-suspeitas")

@bp.route("/blacklist", methods=["GET"])
def ver_blacklist():
    conn = get_connection()

    # Resultado das queries em formato de dicionário/tabela
    conn.row_factory = lambda cursor, row: {
        col[0]: row[idx] for idx, col in enumerate(cursor.description)
    }
    cursor = conn.cursor()

    # Busca todos os registros da blacklist, ordenando pelo mais recente
    cursor.execute("SELECT * FROM blacklist ORDER BY data_registro DESC")
    blacklist = cursor.fetchall()

    conn.close()

    # Renderiza o HTML de visualização da blacklist
    return render_template("ver_blacklist.html", blacklist=blacklist)

@bp.route("/desbloquear", methods=["POST"])
def desbloquear():
    tentativa_id = request.form.get("id")  # ID enviado via formulário
    conn = get_connection()
    cursor = conn.cursor()

    # Busca o código de barras correspondente
    cursor.execute("SELECT codigo_barras FROM tentativas_suspeitas WHERE id = ?", (tentativa_id,))
    row = cursor.fetchone()

    if row:
        codigo_barras = row["codigo_barras"]
        # Remove da blacklist
        cursor.execute("DELETE FROM blacklist WHERE codigo_barras = ?", (codigo_barras,))
        conn.commit()

    conn.close()
    return redirect("/tentativas-suspeitas")

@bp.route("/tentativas-suspeitas/json", methods=["GET"])
def ver_tentativas_json():
    conn = get_connection()
    conn.row_factory = lambda cursor, row: {
        col[0]: row[idx] for idx, col in enumerate(cursor.description)
    }
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tentativas_suspeitas ORDER BY data_verificacao DESC")
    tentativas = cursor.fetchall()

    conn.close()
    return jsonify(tentativas)

@bp.route("/blacklist/json", methods=["GET"])
def ver_blacklist_json():
    conn = get_connection()
    conn.row_factory = lambda cursor, row: {
        col[0]: row[idx] for idx, col in enumerate(cursor.description)
    }
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM blacklist ORDER BY data_registro DESC")
    blacklist = cursor.fetchall()

    conn.close()
    return jsonify(blacklist)
