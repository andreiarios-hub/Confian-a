import re
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import StatusPagamento, StatusServico

HORARIO_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class CustoAdicional(BaseModel):
    descricao: str = ""
    valor: Decimal = Decimal("0")
    status: StatusPagamento = StatusPagamento.PENDENTE
    data_pagamento: Optional[date] = None


class ServicoBase(BaseModel):
    nome_cliente: str = Field(..., min_length=1, max_length=150)
    e_quinto_andar: bool = False
    numero_contrato: Optional[str] = ""
    data: date
    horario: str
    endereco: str = Field(..., min_length=1)
    valor_cobrado: Decimal = Decimal("0")
    custo_operacional: Decimal = Decimal("0")
    custos_adicionais: List[CustoAdicional] = []
    quantidade_ajudantes: int = 0
    viagens_caminhao: int = 0
    observacoes: Optional[str] = ""

    @field_validator("horario")
    @classmethod
    def validar_horario(cls, v: str) -> str:
        if not HORARIO_RE.match(v):
            raise ValueError("horario deve estar no formato HH:MM")
        return v


class ServicoCreate(ServicoBase):
    """Criação de uma nova ordem de serviço (nasce com status AGENDADO)."""

    @model_validator(mode="after")
    def validar_regra_cliente(self) -> "ServicoCreate":
        if self.e_quinto_andar:
            self.nome_cliente = "QuintoAndar"
            if not (self.numero_contrato or "").strip():
                raise ValueError("numero_contrato é obrigatório para serviços QuintoAndar")
        else:
            if not (self.nome_cliente or "").strip():
                raise ValueError("nome_cliente é obrigatório para serviços particulares")
        return self


class ServicoUpdate(BaseModel):
    """Atualização parcial — usada tanto para editar quanto para dar baixa no serviço."""

    nome_cliente: Optional[str] = None
    e_quinto_andar: Optional[bool] = None
    numero_contrato: Optional[str] = None
    data: Optional[date] = None
    horario: Optional[str] = None
    endereco: Optional[str] = None
    valor_cobrado: Optional[Decimal] = None
    custo_operacional: Optional[Decimal] = None
    custos_adicionais: Optional[List[CustoAdicional]] = None
    quantidade_ajudantes: Optional[int] = None
    viagens_caminhao: Optional[int] = None
    efetivos_nomes: Optional[str] = None
    pagamento_efetivos_status: Optional[StatusPagamento] = None
    pagamento_efetivos_data: Optional[date] = None
    status: Optional[StatusServico] = None
    observacoes: Optional[str] = None

    @field_validator("horario")
    @classmethod
    def validar_horario(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HORARIO_RE.match(v):
            raise ValueError("horario deve estar no formato HH:MM")
        return v


class ServicoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome_cliente: str
    e_quinto_andar: bool
    numero_contrato: Optional[str] = ""
    data: date
    horario: str
    endereco: str
    valor_cobrado: Decimal
    custo_operacional: Decimal
    custos_adicionais: List[CustoAdicional]
    custo_total: Decimal
    lucro: Decimal
    quantidade_ajudantes: int
    viagens_caminhao: int
    efetivos_nomes: str
    pagamento_efetivos_status: StatusPagamento
    pagamento_efetivos_data: Optional[date] = None
    status: StatusServico
    observacoes: str
    data_finalizacao: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class WhatsAppLinkOut(BaseModel):
    mensagem: str
    url: str
