import cv2
import numpy as np
import requests
import time
import threading
import torch
from ultralytics import YOLO

# patch de compatibilidade PyTorch
_original_torch_load = torch.load
torch.load = lambda *args, **kwargs: _original_torch_load(*args, **{**kwargs, "weights_only": False})

# configurações do Telegram
TELEGRAM_TOKEN = "8759135607:AAHuS-PaT-qnsTzI-40miPWaizK9fHl0JSI"
CHAT_ID = "1774859395"

INTERVALO_ALERTA = 10 
ultimo_envio = 0

def enviar_telegram_async(mensagem, caminho_imagem):
    def worker():
        try:
            url_text = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url_text, data={"chat_id": CHAT_ID, "text": mensagem}, timeout=10)
            
            if caminho_imagem:
                url_photo = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
                with open(caminho_imagem, "rb") as photo:
                    requests.post(url_photo, data={"chat_id": CHAT_ID}, files={"photo": photo}, timeout=10)
            print("✅ Notificação enviada para o Telegram com sucesso!")
        except Exception as e:
            print(f"⚠️ Erro ao enviar notificação: {e}")

    threading.Thread(target=worker, daemon=True).start()

def tem_capacete_branco(crop_cabeca):
    """Verifica se há cor branca predominante na região superior (cabeça)."""
    if crop_cabeca.size == 0:
        return False
    
    hsv = cv2.cvtColor(crop_cabeca, cv2.COLOR_BGR2HSV)
    # Faixa da cor branca no espaço HSV
    lower_white = np.array([0, 0, 160])
    upper_white = np.array([180, 60, 255])
    
    mask = cv2.inRange(hsv, lower_white, upper_white)
    proporcao_branco = cv2.countNonZero(mask) / (crop_cabeca.shape[0] * crop_cabeca.shape[1])
    
    return proporcao_branco > 0.25  # pelo menos 25% de branco na área superior

# carrega o modelo local yolov8n.pt
print("📦 Carregando modelo local...")
model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Erro ao abrir a câmera.")
    exit()

print("🎥 Monitoramento ativo. Pressione 'q' para fechar.")

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, verbose=False)
        alerta_infracao = False

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = model.names[cls_id].lower()

                # Se encontrar uma pessoa
                if label == "person":
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Corta a parte superior do corpo (onde fica o capacete/cabeça)
                    altura = y2 - y1
                    cabea_y2 = y1 + int(altura * 0.3)  # Pega os 30% superiores da caixa
                    crop_cabeca = frame[y1:cabea_y2, x1:x2]

                    # Testa se tem capacete branco na cabeça
                    if tem_capacete_branco(crop_cabeca):
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, "CAPACETE BRANCO OK", (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    else:
                        alerta_infracao = True
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(frame, "SEM CAPACETE BRANCO", (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        tempo_atual = time.time()
        if alerta_infracao and (tempo_atual - ultimo_envio > INTERVALO_ALERTA):
            ultimo_envio = tempo_atual
            caminho_alerta = "alerta_epi.jpg"
            cv2.imwrite(caminho_alerta, frame)
            enviar_telegram_async("⚠️ ALERTA: foto do trabalhador detectado sem capacete branco,pfv avisar para colocar o epi pela segurança!!", caminho_alerta)

        cv2.imshow("Monitoramento de EPI", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    print("🛑 Monitoramento encerrado com sucesso.")