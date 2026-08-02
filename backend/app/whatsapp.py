from datetime import date
from typing import Tuple
from urllib.parse import quote

from . import models


def _data_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def montar_mensagem(servico: models.OrdemServico) -> str:
    # Igual ao buildWhatsAppMessage() do frontend: só data, horário e
    # endereço — sem cliente, contrato, valores ou observações.
    linhas = [
        "📦 *NOVA ORDEM DE SERVIÇO*",
        "_Confiança Depósito e Armazenamento_",
        "",
        f"📅 *Data:* {_data_br(servico.data_horario.date())}",
        f"🕐 *Horário:* {servico.data_horario.strftime('%H:%M')}",
        f"📍 *Endereço:* {servico.endereco}",
        "",
        "Confirmar recebimento ✅",
    ]
    return "\n".join(linhas)


def montar_link(servico: models.OrdemServico) -> Tuple[str, str]:
    mensagem = montar_mensagem(servico)
    url = f"https://wa.me/?text={quote(mensagem)}"
    return mensagem, url
