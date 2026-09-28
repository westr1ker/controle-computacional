import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")
    WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
    WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY")
    GESTOR_TELEFONE = os.getenv("GESTOR_TELEFONE")
    CAMERA_SOURCE = int(os.getenv("CAMERA_SOURCE", 0))
    INTERVALO_ALERTA = int(os.getenv("INTERVALO_ALERTA_SEGUNDOS", 10))

settings = Settings()