# utils.py
from database import get_connection

def registrar_log(acao, origem, dados):
    """
    Registra uma ação no log do sistema.

    :param acao: Nome da ação executada (ex: "registro_boleto")
    :param origem: Identificador da origem (ex: CNPJ, token, "usuário")
    :param dados: Descrição ou conteúdo relevante do evento
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO log_eventos (acao, origem, dados)
            VALUES (?, ?, ?)
        """, (acao, origem, dados))
        conn.commit()
    except Exception as e:
        print(f"[ERRO AO REGISTRAR LOG] {e}")
    finally:
        conn.close()
