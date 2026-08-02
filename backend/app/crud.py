from datetime import date as date_
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


def _combinar_data_horario(data: date_, horario: str) -> datetime:
    hora, minuto = map(int, horario.split(":"))
    return datetime(data.year, data.month, data.day, hora, minuto)


def _serializar_custos(itens: List[schemas.CustoAdicional]) -> list:
    return [{"descricao": (item.descricao or "").strip(), "valor": float(item.valor or 0)} for item in itens]


def _custo_total(servico: models.OrdemServico) -> Decimal:
    extras = sum(
        (Decimal(str(c.get("valor", 0))) for c in (servico.custos_adicionais or [])),
        Decimal("0"),
    )
    return Decimal(str(servico.custo_operacional or 0)) + extras


def to_out(servico: models.OrdemServico) -> schemas.ServicoOut:
    total = _custo_total(servico)
    lucro = Decimal(str(servico.valor_cobrado or 0)) - total
    return schemas.ServicoOut(
        id=servico.id,
        nome_cliente=servico.nome_cliente,
        e_quinto_andar=servico.e_quinto_andar,
        numero_contrato=servico.numero_contrato or "",
        data=servico.data_horario.date(),
        horario=servico.data_horario.strftime("%H:%M"),
        endereco=servico.endereco,
        valor_cobrado=servico.valor_cobrado,
        custo_operacional=servico.custo_operacional,
        custos_adicionais=servico.custos_adicionais or [],
        custo_total=total,
        lucro=lucro,
        quantidade_ajudantes=servico.quantidade_ajudantes,
        viagens_caminhao=servico.viagens_caminhao,
        efetivos_nomes=servico.efetivos_nomes or "",
        status=servico.status,
        observacoes=servico.observacoes or "",
        data_finalizacao=servico.data_finalizacao,
        created_at=servico.created_at,
        updated_at=servico.updated_at,
    )


def criar_servico(db: Session, dados: schemas.ServicoCreate) -> models.OrdemServico:
    servico = models.OrdemServico(
        nome_cliente=dados.nome_cliente,
        e_quinto_andar=dados.e_quinto_andar,
        numero_contrato=dados.numero_contrato or "",
        data_horario=_combinar_data_horario(dados.data, dados.horario),
        endereco=dados.endereco,
        valor_cobrado=dados.valor_cobrado,
        custo_operacional=dados.custo_operacional,
        custos_adicionais=_serializar_custos(dados.custos_adicionais),
        quantidade_ajudantes=dados.quantidade_ajudantes,
        viagens_caminhao=dados.viagens_caminhao,
        efetivos_nomes="",
        status=models.StatusServico.AGENDADO,
        observacoes=dados.observacoes or "",
        data_finalizacao=None,
    )
    db.add(servico)
    db.commit()
    db.refresh(servico)
    return servico


def obter_servico(db: Session, servico_id: str) -> Optional[models.OrdemServico]:
    return db.query(models.OrdemServico).filter(models.OrdemServico.id == servico_id).first()


def listar_servicos(
    db: Session,
    data_inicio: Optional[date_] = None,
    data_fim: Optional[date_] = None,
    status: Optional[models.StatusServico] = None,
    cliente: Optional[str] = None,
    somente_quinto_andar: Optional[bool] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[models.OrdemServico]:
    query = db.query(models.OrdemServico)
    if data_inicio:
        query = query.filter(
            models.OrdemServico.data_horario >= datetime(data_inicio.year, data_inicio.month, data_inicio.day)
        )
    if data_fim:
        fim = datetime(data_fim.year, data_fim.month, data_fim.day, 23, 59, 59)
        query = query.filter(models.OrdemServico.data_horario <= fim)
    if status:
        query = query.filter(models.OrdemServico.status == status)
    if cliente:
        query = query.filter(models.OrdemServico.nome_cliente.ilike(f"%{cliente}%"))
    if somente_quinto_andar is not None:
        query = query.filter(models.OrdemServico.e_quinto_andar == somente_quinto_andar)
    return query.order_by(models.OrdemServico.data_horario.asc()).offset(skip).limit(limit).all()


def atualizar_servico(
    db: Session, servico: models.OrdemServico, dados: schemas.ServicoUpdate
) -> models.OrdemServico:
    payload = dados.model_dump(exclude_unset=True, exclude={"data", "horario", "custos_adicionais"})

    if dados.data is not None or dados.horario is not None:
        data_atual = dados.data or servico.data_horario.date()
        horario_atual = dados.horario or servico.data_horario.strftime("%H:%M")
        servico.data_horario = _combinar_data_horario(data_atual, horario_atual)

    if dados.custos_adicionais is not None:
        payload["custos_adicionais"] = _serializar_custos(dados.custos_adicionais)

    for campo, valor in payload.items():
        setattr(servico, campo, valor)

    if dados.status in (models.StatusServico.CONCLUIDO, models.StatusServico.CANCELADO) and not servico.data_finalizacao:
        servico.data_finalizacao = date_.today()

    db.add(servico)
    db.commit()
    db.refresh(servico)
    return servico


def listar_quinto_andar_concluidos(db: Session, mes: int, ano: int) -> List[models.OrdemServico]:
    inicio = datetime(ano, mes, 1)
    fim = datetime(ano + 1, 1, 1) if mes == 12 else datetime(ano, mes + 1, 1)
    return (
        db.query(models.OrdemServico)
        .filter(
            models.OrdemServico.e_quinto_andar.is_(True),
            models.OrdemServico.status == models.StatusServico.CONCLUIDO,
            models.OrdemServico.data_horario >= inicio,
            models.OrdemServico.data_horario < fim,
        )
        .order_by(models.OrdemServico.data_horario.asc())
        .all()
    )


def listar_para_relatorio_geral(
    db: Session,
    mes: Optional[int],
    ano: Optional[int],
    tipo: str,
    status: Optional[models.StatusServico],
) -> List[models.OrdemServico]:
    query = db.query(models.OrdemServico)
    if mes and ano:
        inicio = datetime(ano, mes, 1)
        fim = datetime(ano + 1, 1, 1) if mes == 12 else datetime(ano, mes + 1, 1)
        query = query.filter(models.OrdemServico.data_horario >= inicio, models.OrdemServico.data_horario < fim)
    if tipo == "QuintoAndar":
        query = query.filter(models.OrdemServico.e_quinto_andar.is_(True))
    elif tipo == "Particular":
        query = query.filter(models.OrdemServico.e_quinto_andar.is_(False))
    if status:
        query = query.filter(models.OrdemServico.status == status)
    return query.order_by(models.OrdemServico.data_horario.asc()).all()
