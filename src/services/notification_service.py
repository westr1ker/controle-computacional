import requests
import logging
from src.config.settings import settings

def notificar_infracao_whatsapp(nome_operador, detalhe_infracao=""):
    """
    Envia notificação formatada para o Telegram.
    Exemplo de saída: "TI Weslley sem EPI" ou "PINTORES João sem EPI"
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not bot_token or not chat_id:
        logging.warning("Telegram Bot Token ou Chat ID não configurados.")
        return

    # Formatação limpa do texto para a notificação
    # Transforma "Weslley Santos (TI)" -> "TI Weslley Santos sem EPI"
    if "(" in nome_operador and ")" in nome_operador:
        partes = nome_operador.split("(")
        nome = partes[0].strip()
        setor = partes[1].replace(")", "").strip()
        mensagem_texto = f"🚨 *{setor} {nome} sem EPI*"
    else:
        mensagem_texto = f"🚨 *{nome_operador} sem EPI*"

    payload = {
        "chat_id": chat_id,
        "text": mensagem_texto,
        "parse_mode": "Markdown"
    }

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logging.info(f"Notificação enviada: {mensagem_texto}")
        else:
            logging.error(f"Falha ao enviar mensagem para o Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Erro de conexão com o Telegram: {e}")