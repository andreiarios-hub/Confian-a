from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/custos-gerais", tags=["Custos Gerais"])


@router.post("", response_model=schemas.CustoGeralOut, status_code=http_status.HTTP_201_CREATED)
def criar_custo_geral(dados: schemas.CustoGeralCreate, db: Session = Depends(get_db)):
    """Custo adicional geral da operação (papel bolha, fita, contador, taxas
    etc.) — lançado manualmente, sem vínculo com um serviço específico."""
    custo = crud.criar_custo_geral(db, dados)
    return custo


@router.get("", response_model=List[schemas.CustoGeralOut])
def listar_custos_gerais(db: Session = Depends(get_db)):
    return crud.listar_custos_gerais(db)


@router.patch("/{custo_id}", response_model=schemas.CustoGeralOut)
def atualizar_custo_geral(custo_id: str, dados: schemas.CustoGeralUpdate, db: Session = Depends(get_db)):
    custo = crud.obter_custo_geral(db, custo_id)
    if not custo:
        raise HTTPException(status_code=404, detail="Custo adicional não encontrado")
    return crud.atualizar_custo_geral(db, custo, dados)


@router.delete("/{custo_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def excluir_custo_geral(custo_id: str, db: Session = Depends(get_db)):
    custo = crud.obter_custo_geral(db, custo_id)
    if not custo:
        raise HTTPException(status_code=404, detail="Custo adicional não encontrado")
    crud.excluir_custo_geral(db, custo)
