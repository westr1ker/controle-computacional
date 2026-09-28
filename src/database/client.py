import logging

db = None

# nesse momento tento carregar o prismaa de forma segura caso a versão do Python permita
try:
    from prisma import Prisma
    db = Prisma()
except Exception as e:
    logging.warning(f"Prisma não pôde ser carregado nesta versão do Python: {e}")

def init_db():
    if db is None:
        logging.warning("Executando em modo local (Sem persistência em banco de dados).")
        return
    try:
        db.connect()
        logging.info("Conexão com banco de dados estabelecida com sucesso.")
    except Exception as e:
        logging.warning(f"Não foi possível conectar ao banco de dados: {e}")

def registrar_ocorrencia(funcionario_id: int, tipo_infracao: str):
    if db is None or not db.is_connected():
        logging.info(f"[SIMULAÇÃO] Ocorrência gravada localmente para o funcionário ID {funcionario_id}.")
        return
    try:
        db.ocorrencia.create(
            data={
                'funcionarioId': funcionario_id,
                'tipoInfracao': tipo_infracao
            }
        )
        logging.info(f"Ocorrência registrada no banco para o funcionário ID {funcionario_id}.")
    except Exception as e:
        logging.error(f"Erro ao salvar ocorrência no banco: {e}")