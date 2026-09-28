import cv2
import time
import logging
import os
import torch
from ultralytics import YOLO
from deepface import DeepFace
from src.config.settings import settings
from src.database.client import registrar_ocorrencia
from src.services.notification_service import notificar_infracao_whatsapp

# Compatibilidade para PyTorch 2.6+
_original_torch_load = torch.load

def _custom_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)

torch.load = _custom_torch_load


class EPIDetector:
    def __init__(self):
        self.model = YOLO('yolov8n.pt') 
        self.cap = cv2.VideoCapture(settings.CAMERA_SOURCE)
        self.ultimo_alerta = 0
        self.lista_setores = ["pintores", "ti"]

    def identificar_operador(self, frame_pessoa):
        """Identifica o rosto comparando com as imagens dentro das pastas de setores."""
        if frame_pessoa.size == 0:
            return "Desconhecido / Visitante"

        for setor in self.lista_setores:
            if os.path.exists(setor) and len(os.listdir(setor)) > 0:
                try:
                    dfs = DeepFace.find(
                        img_path=frame_pessoa,
                        db_path=setor,
                        model_name="VGG-Face",
                        enforce_detection=False,
                        silent=True
                    )
                    
                    if len(dfs) > 0 and not dfs[0].empty:
                        caminho_imagem = dfs[0]['identity'].iloc[0]
                        nome_arquivo = os.path.basename(caminho_imagem)
                        nome = os.path.splitext(nome_arquivo)[0].replace("_", " ").title()
                        return f"{nome} ({setor.upper()})"
                except Exception as e:
                    logging.debug(f"Processamento de rosto omitido: {e}")

        return "Desconhecido / Visitante"

    def processar_frame(self, frame):
        results = self.model(frame, verbose=False)
        operadores_em_risco = 0
        detalhe_infracao = ""
        identificacao_pessoa = "Desconhecido / Visitante"

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                classe_nome = self.model.names[cls_id]

                if conf > 0.5 and classe_nome in ['person', 'sem_capacete', 'sem_oculos']:
                    operadores_em_risco += 1
                    detalhe_infracao = f"Ausência de EPI ({classe_nome})"
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    pessoa_crop = frame[y1:y2, x1:x2]
                    
                    identificacao_pessoa = self.identificar_operador(pessoa_crop)

                    cor_caixa = (0, 165, 255) if "Desconhecido" not in identificacao_pessoa else (0, 0, 255)
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), cor_caixa, 2)
                    cv2.putText(
                        frame, 
                        f"{identificacao_pessoa} - Sem EPI", 
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, 
                        cor_caixa, 
                        2
                    )

        return frame, operadores_em_risco, detalhe_infracao, identificacao_pessoa

    def run(self):
        if not self.cap.isOpened():
            logging.error("Falha ao acessar o dispositivo de câmera.")
            return

        logging.info("Sistema de Auditoria XIMED iniciado.")

        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                break

            frame_processado, qtd_risco, tipo_infracao, pessoa_detectada = self.processar_frame(frame)
            tempo_atual = time.time()

            if qtd_risco > 0 and (tempo_atual - self.ultimo_alerta > settings.INTERVALO_ALERTA):
                mensagem_log = f"Infração detectada: {pessoa_detectada} - {tipo_infracao}"
                logging.warning(mensagem_log)
                
                registrar_ocorrencia(funcionario_id=1, tipo_infracao=mensagem_log)
                notificar_infracao_whatsapp(pessoa_detectada, detalhe_infracao=tipo_infracao)
                
                self.ultimo_alerta = tempo_atual

            cv2.rectangle(frame_processado, (10, 10), (450, 60), (0, 0, 0), -1)
            cv2.putText(frame_processado, "AUDITORIA XIMED - MULTI-SETORES", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame_processado, f"Infrações em Risco: {qtd_risco}", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

            cv2.imshow("Monitoramento de EPI - Visao Computacional", frame_processado)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()