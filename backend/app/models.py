import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Enum, Integer, Numeric, String, Text

from .database import Base


class StatusServico(str, enum.Enum):
    AGENDADO = "AGENDADO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"


class OrdemServico(Base):
    __tablename__ = "ordens_servico"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    nome_cliente = Column(String(150), nullable=False)
    e_quinto_andar = Column(Boolean, nullable=False, default=False, index=True)
    numero_contrato = Column(String(60), nullable=True, default="")

    data_horario = Column(DateTime, nullable=False, index=True)
    endereco = Column(Text, nullable=False)

    valor_cobrado = Column(Numeric(12, 2), nullable=False, default=0)
    custo_operacional = Column(Numeric(12, 2), nullable=False, default=0)
    # Lista de objetos {"descricao": str, "valor": float} — guincho, munck, etc.
    custos_adicionais = Column(JSON, nullable=False, default=list)

    quantidade_ajudantes = Column(Integer, nullable=False, default=0)
    viagens_caminhao = Column(Integer, nullable=False, default=0)
    efetivos_nomes = Column(Text, nullable=False, default="")

    status = Column(Enum(StatusServico), nullable=False, default=StatusServico.AGENDADO, index=True)
    observacoes = Column(Text, nullable=False, default="")
    data_finalizacao = Column(Date, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
