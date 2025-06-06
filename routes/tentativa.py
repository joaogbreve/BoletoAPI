from flask import Blueprint, render_template, request, redirect, jsonify
from database import get_connection

bp = Blueprint("tentativas", __name__)

@bp.route("/tentativas-suspeitas", methods=["GET"])
def ver_tentativas():
    conn = get_connection()
    conn.row_factory = lambda cursor, row: {
        col[0]: row[idx] for idx, col in enumerate(cursor.description)
    }
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tentativas_suspeitas ORDER BY data_verificacao DESC")
    tentativas = cursor.fetchall()

    # Pega todos os códigos já bloqueados
    cursor.execute("SELECT codigo_barras FROM blacklist")
    codigos_bloqueados = {row["codigo_barras"] for row in cursor.fetchall()}

    conn.close()
    return render_template("ver_tentativas_suspeitas.html", tentativas=tentativas, codigos_bloqueados=codigos_bloqueados)

@bp.route("/bloquear", methods=["POST"])
def bloquear_tentativa():
    tentativa_id = request.form.get("id")
    conn = get_connection()
    cursor = conn.cursor()

    # Busca os dados da tentativa suspeita
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
    conn.row_factory = lambda cursor, row: {
        col[0]: row[idx] for idx, col in enumerate(cursor.description)
    }
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM blacklist ORDER BY data_registro DESC")
    blacklist = cursor.fetchall()

    conn.close()
    return render_template("ver_blacklist.html", blacklist=blacklist)

@bp.route("/desbloquear", methods=["POST"])
def desbloquear():
    tentativa_id = request.form.get("id")
    conn = get_connection()
    cursor = conn.cursor()

    # Pegar o codigo_barras da tentativa
    cursor.execute("SELECT codigo_barras FROM tentativas_suspeitas WHERE id = ?", (tentativa_id,))
    row = cursor.fetchone()

    if row:
        codigo_barras = row["codigo_barras"]
        cursor.execute("DELETE FROM blacklist WHERE codigo_barras = ?", (codigo_barras,))
        conn.commit()

    conn.close()
    return redirect("/tentativas-suspeitas")