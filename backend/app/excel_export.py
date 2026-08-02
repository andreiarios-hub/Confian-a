from decimal import Decimal
from io import BytesIO
from typing import Callable, List, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from . import models

FORMATO_DATA = "DD/MM/YYYY"
FORMATO_HORA = "H:MM"
FORMATO_MOEDA = '"R$" #,##0.00;-"R$" #,##0.00'

COR_CABECALHO = "1E293B"  # slate-900, mesma cor do header do painel
COR_TEXTO_CABECALHO = "FFFFFF"
COR_BORDA = "CBD5E1"  # slate-300


class Coluna:
    def __init__(self, header: str, valor: Callable[[models.OrdemServico], object], tipo: str, largura: int):
        self.header = header
        self.valor = valor
        self.tipo = tipo
        self.largura = largura


def _custo_total(servico: models.OrdemServico) -> Decimal:
    extras = sum(
        (Decimal(str(c.get("valor", 0))) for c in (servico.custos_adicionais or [])),
        Decimal("0"),
    )
    return Decimal(str(servico.custo_operacional or 0)) + extras


def _lucro(servico: models.OrdemServico) -> Decimal:
    return Decimal(str(servico.valor_cobrado or 0)) - _custo_total(servico)


def _texto_obs_com_extras(servico: models.OrdemServico) -> str:
    extras = [c for c in (servico.custos_adicionais or []) if c.get("descricao") or c.get("valor")]
    partes = []
    if servico.observacoes:
        partes.append(servico.observacoes)
    if extras:
        detalhes = ", ".join(f"{c.get('descricao') or 'item'} R$ {float(c.get('valor', 0)):.2f}" for c in extras)
        partes.append(f"Custos extras: {detalhes}")
    return " | ".join(partes)


# 🔧 Mesma ideia do MAPEAMENTO_COLUNAS_QUINTOANDAR do frontend: única lista
# que precisa mudar se o QuintoAndar alterar nome/ordem/quantidade de colunas.
MAPEAMENTO_QUINTO_ANDAR: List[Coluna] = [
    Coluna("Data", lambda s: s.data_horario.date(), "data", 12),
    Coluna("Endereço", lambda s: s.endereco, "texto", 60),
    Coluna("Horário", lambda s: s.data_horario.strftime("%H:%M"), "hora", 10),
    Coluna("Contrato", lambda s: s.numero_contrato or "", "texto", 22),
    Coluna("Custo", lambda s: _custo_total(s), "moeda", 18),
    Coluna("Obs.", lambda s: _texto_obs_com_extras(s), "texto", 60),
]

MAPEAMENTO_GERAL: List[Coluna] = [
    Coluna("Data", lambda s: s.data_horario.date(), "data", 12),
    Coluna("Horário", lambda s: s.data_horario.strftime("%H:%M"), "hora", 10),
    Coluna("Tipo", lambda s: "QuintoAndar" if s.e_quinto_andar else "Particular", "texto", 14),
    Coluna("Cliente", lambda s: s.nome_cliente, "texto", 24),
    Coluna("Contrato", lambda s: s.numero_contrato or "", "texto", 14),
    Coluna("Endereço", lambda s: s.endereco, "texto", 50),
    Coluna("Status", lambda s: s.status.value, "texto", 14),
    Coluna("Valor Cobrado", lambda s: Decimal(str(s.valor_cobrado or 0)), "moeda", 16),
    Coluna("Custo Operacional", lambda s: Decimal(str(s.custo_operacional or 0)), "moeda", 18),
    Coluna(
        "Custos Adicionais",
        lambda s: sum((Decimal(str(c.get("valor", 0))) for c in (s.custos_adicionais or [])), Decimal("0")),
        "moeda",
        18,
    ),
    Coluna("Custo Total", lambda s: _custo_total(s), "moeda", 16),
    Coluna("Lucro", lambda s: _lucro(s), "moeda", 16),
    Coluna("Obs.", lambda s: _texto_obs_com_extras(s), "texto", 50),
]


def _escrever_celula(ws: Worksheet, linha: int, coluna: int, valor, tipo: str):
    celula = ws.cell(row=linha, column=coluna, value=valor)
    if tipo == "data":
        celula.number_format = FORMATO_DATA
    elif tipo == "hora":
        celula.number_format = FORMATO_HORA
    elif tipo == "moeda":
        celula.number_format = FORMATO_MOEDA
    return celula


def _construir_planilha(
    nome_aba: str,
    servicos: Sequence[models.OrdemServico],
    mapeamento: List[Coluna],
    linha_inicial_dados: int,
) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = nome_aba

    fonte_cabecalho = Font(name="Poppins", size=11, bold=True, color=COR_TEXTO_CABECALHO)
    preenchimento_cabecalho = PatternFill(start_color=COR_CABECALHO, end_color=COR_CABECALHO, fill_type="solid")
    borda_fina = Border(
        left=Side(style="thin", color=COR_BORDA),
        right=Side(style="thin", color=COR_BORDA),
        top=Side(style="thin", color=COR_BORDA),
        bottom=Side(style="thin", color=COR_BORDA),
    )

    for c, col in enumerate(mapeamento, start=1):
        celula = ws.cell(row=1, column=c, value=col.header)
        celula.font = fonte_cabecalho
        celula.fill = preenchimento_cabecalho
        celula.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(c)].width = col.largura
    ws.row_dimensions[1].height = 22

    for r, servico in enumerate(servicos):
        linha = linha_inicial_dados + r
        for c, col in enumerate(mapeamento, start=1):
            celula = _escrever_celula(ws, linha, c, col.valor(servico), col.tipo)
            celula.border = borda_fina
            celula.font = Font(name="Poppins", size=10)
            celula.alignment = Alignment(vertical="top", wrap_text=col.tipo == "texto")

    ws.freeze_panes = f"A{linha_inicial_dados}"
    return wb


def gerar_relatorio_quinto_andar(servicos: Sequence[models.OrdemServico]) -> BytesIO:
    # LINHA_INICIAL_DADOS = 3, igual ao frontend: cabeçalho na linha 1,
    # linha 2 em branco (espaço reservado pelo modelo oficial do QuintoAndar).
    wb = _construir_planilha("Planilha1", servicos, MAPEAMENTO_QUINTO_ANDAR, linha_inicial_dados=3)
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def gerar_relatorio_geral(servicos: Sequence[models.OrdemServico]) -> BytesIO:
    wb = _construir_planilha("Relatório Geral", servicos, MAPEAMENTO_GERAL, linha_inicial_dados=2)
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
