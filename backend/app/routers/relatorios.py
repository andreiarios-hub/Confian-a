from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, excel_export, models
from ..database import get_db

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios"])

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/quinto-andar/exportar")
def exportar_quinto_andar(
    mes: int = Query(..., ge=1, le=12, description="Mês de referência (1-12)"),
    ano: int = Query(..., ge=2000, le=2100, description="Ano de referência"),
    db: Session = Depends(get_db),
):
    """Serviços QuintoAndar CONCLUIDOS no período, no modelo exigido pelo contrato."""
    servicos = crud.listar_quinto_andar_concluidos(db, mes, ano)
    if not servicos:
        raise HTTPException(status_code=404, detail="Nenhum serviço QuintoAndar concluído nesse período")

    buffer = excel_export.gerar_relatorio_quinto_andar(servicos)
    nome_arquivo = f"Relatorio_QuintoAndar_{ano:04d}-{mes:02d}.xlsx"
    return StreamingResponse(
        buffer,
        media_type=MIME_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@router.get("/geral/exportar")
def exportar_geral(
    mes: Optional[int] = Query(None, ge=1, le=12),
    ano: Optional[int] = Query(None, ge=2000, le=2100),
    tipo: str = Query("Todos", pattern="^(Todos|QuintoAndar|Particular)$"),
    status: Optional[models.StatusServico] = Query(None),
    db: Session = Depends(get_db),
):
    """Relatório geral (QuintoAndar + Particular) — mesmo recurso da aba 'Relatório Geral' do painel."""
    servicos = crud.listar_para_relatorio_geral(db, mes, ano, tipo, status)
    if not servicos:
        raise HTTPException(status_code=404, detail="Nenhum serviço encontrado com esses filtros")

    buffer = excel_export.gerar_relatorio_geral(servicos)
    sufixo = f"{ano:04d}-{mes:02d}" if (mes and ano) else "Todos"
    nome_arquivo = f"Relatorio_Geral_{sufixo}.xlsx"
    return StreamingResponse(
        buffer,
        media_type=MIME_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )
