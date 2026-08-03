from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from .. import crud, models, schemas, whatsapp
from ..database import get_db

router = APIRouter(prefix="/api/servicos", tags=["Serviços"])


@router.post("", response_model=schemas.ServicoOut, status_code=http_status.HTTP_201_CREATED)
def criar_servico(dados: schemas.ServicoCreate, db: Session = Depends(get_db)):
    """Cria um novo agendamento de depósito judiciário (nasce como AGENDADO)."""
    servico = crud.criar_servico(db, dados)
    return crud.to_out(servico)


@router.get("", response_model=List[schemas.ServicoOut])
def listar_servicos(
    data_inicio: Optional[date] = Query(None, description="Filtra serviços a partir desta data"),
    data_fim: Optional[date] = Query(None, description="Filtra serviços até esta data"),
    status: Optional[models.StatusServico] = Query(None, description="Filtra por status"),
    cliente: Optional[str] = Query(None, description="Busca parcial pelo nome do cliente"),
    somente_quinto_andar: Optional[bool] = Query(None, description="Filtra apenas contratos QuintoAndar"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    servicos = crud.listar_servicos(
        db,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status,
        cliente=cliente,
        somente_quinto_andar=somente_quinto_andar,
        skip=skip,
        limit=limit,
    )
    return [crud.to_out(s) for s in servicos]


@router.get("/{servico_id}", response_model=schemas.ServicoOut)
def obter_servico(servico_id: str, db: Session = Depends(get_db)):
    servico = crud.obter_servico(db, servico_id)
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return crud.to_out(servico)


@router.patch("/{servico_id}", response_model=schemas.ServicoOut)
def atualizar_servico(servico_id: str, dados: schemas.ServicoUpdate, db: Session = Depends(get_db)):
    """Baixa do serviço: atualiza efetivos, viagens, custos e status final (também serve para edição geral)."""
    servico = crud.obter_servico(db, servico_id)
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    servico = crud.atualizar_servico(db, servico, dados)
    return crud.to_out(servico)


@router.get("/{servico_id}/whatsapp-link", response_model=schemas.WhatsAppLinkOut)
def whatsapp_link(servico_id: str, db: Session = Depends(get_db)):
    servico = crud.obter_servico(db, servico_id)
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    mensagem, url = whatsapp.montar_link(servico)
    return schemas.WhatsAppLinkOut(mensagem=mensagem, url=url)


@router.delete("/{servico_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def excluir_servico(servico_id: str, db: Session = Depends(get_db)):
    servico = crud.obter_servico(db, servico_id)
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    crud.excluir_servico(db, servico)
