"""Sanitiza observações duplicadas gravadas antes da correção do bug de
concatenação na tela de baixa (a edição repetida de um serviço concatenava
o texto novo ao texto antigo, gerando strings como
"01 viagem do Robinho sem ajudantes | 01 Caminhão | 01 Caminhão | 01 Caminhão").

Este script varre a tabela ordens_servico e, para cada registro cuja
observação contenha o separador " | ", remove trechos duplicados (mesmo
texto repetido), preservando a ordem da primeira ocorrência e o restante do
conteúdo intacto. Não deleta nem reescreve texto que não seja uma repetição
exata de um trecho já visto.

Uso (a partir da pasta backend/):
    # Por padrão roda em modo "dry-run": só mostra o que mudaria, não grava nada.
    python scripts/limpar_observacoes_duplicadas.py

    # Para gravar as mudanças no banco (usa DATABASE_URL do ambiente/.env):
    python scripts/limpar_observacoes_duplicadas.py --apply

Rodar a partir da pasta backend/, com o DATABASE_URL apontando para o banco
que se quer limpar (Neon em produção, ou sqlite local para testar antes).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402


def sanitizar_texto(texto: str) -> str:
    """Remove trechos exatamente repetidos, separados por ' | ', mantendo a
    ordem da primeira ocorrência. Idempotente: rodar duas vezes no mesmo
    texto produz o mesmo resultado."""
    if not texto or "|" not in texto:
        return texto

    partes_originais = [p.strip() for p in texto.split("|")]
    vistas = set()
    partes_unicas = []
    for parte in partes_originais:
        if not parte:
            continue
        chave = parte.casefold()
        if chave in vistas:
            continue
        vistas.add(chave)
        partes_unicas.append(parte)

    return " | ".join(partes_unicas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava as mudanças no banco. Sem essa flag, apenas mostra o que seria alterado.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        servicos = db.query(models.OrdemServico).all()
        alterados = []
        for servico in servicos:
            original = servico.observacoes or ""
            corrigido = sanitizar_texto(original)
            if corrigido != original:
                alterados.append((servico, original, corrigido))

        if not alterados:
            print("Nenhuma observação duplicada encontrada.")
            return

        print(f"{len(alterados)} registro(s) com observação duplicada:\n")
        for servico, original, corrigido in alterados:
            print(f"  id={servico.id} cliente={servico.nome_cliente!r}")
            print(f"    antes:  {original!r}")
            print(f"    depois: {corrigido!r}\n")

        if args.apply:
            for servico, _original, corrigido in alterados:
                servico.observacoes = corrigido
                db.add(servico)
            db.commit()
            print(f"{len(alterados)} registro(s) atualizado(s) no banco.")
        else:
            print("Modo dry-run (nenhuma alteração gravada). Rode novamente com --apply para gravar.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
