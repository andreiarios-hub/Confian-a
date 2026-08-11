"""Remove registros duplicados de ordens_servico criados pelo bug de duplicação
ao editar/salvar (edição que caía no fluxo de criação — POST — em vez de
atualização — PATCH —, gerando uma cópia nova do mesmo atendimento).

Considera duplicado um grupo de registros com os mesmos valores em:
  nome_cliente, e_quinto_andar, numero_contrato, data_horario, endereco

Dentro de cada grupo duplicado, mantém o registro mais "completo/recente"
(critério: maior updated_at; em empate, o que tem status mais avançado —
CONCLUIDO/CANCELADO > EM_ANDAMENTO > AGENDADO — depois maior created_at) e
remove os demais.

Uso (a partir da pasta backend/):
    # Por padrão roda em modo "dry-run": só mostra o que seria removido.
    python scripts/remover_duplicados.py

    # Para gravar (apagar) os duplicados no banco (usa DATABASE_URL do
    # ambiente/.env — aponte para o banco certo antes de rodar com --apply):
    python scripts/remover_duplicados.py --apply
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402

PRIORIDADE_STATUS = {
    models.StatusServico.CONCLUIDO: 3,
    models.StatusServico.CANCELADO: 3,
    models.StatusServico.EM_ANDAMENTO: 2,
    models.StatusServico.AGENDADO: 1,
}


def chave(servico: models.OrdemServico):
    return (
        (servico.nome_cliente or "").strip().casefold(),
        bool(servico.e_quinto_andar),
        (servico.numero_contrato or "").strip().casefold(),
        servico.data_horario,
        (servico.endereco or "").strip().casefold(),
    )


def escolher_mantido(grupo):
    return sorted(
        grupo,
        key=lambda s: (PRIORIDADE_STATUS.get(s.status, 0), s.updated_at, s.created_at),
        reverse=True,
    )[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apaga de fato os duplicados. Sem essa flag, apenas mostra o que seria removido.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        servicos = db.query(models.OrdemServico).all()
        grupos = defaultdict(list)
        for s in servicos:
            grupos[chave(s)].append(s)

        grupos_duplicados = {k: v for k, v in grupos.items() if len(v) > 1}

        if not grupos_duplicados:
            print("Nenhum registro duplicado encontrado.")
            return

        total_remover = 0
        for k, grupo in grupos_duplicados.items():
            mantido = escolher_mantido(grupo)
            remover = [s for s in grupo if s.id != mantido.id]
            total_remover += len(remover)
            print(f"Grupo: cliente={mantido.nome_cliente!r} data={mantido.data_horario} endereco={mantido.endereco!r}")
            print(f"  mantém: id={mantido.id} status={mantido.status} updated_at={mantido.updated_at}")
            for s in remover:
                print(f"  remove: id={s.id} status={s.status} updated_at={s.updated_at}")
            print()

        print(f"Total: {len(grupos_duplicados)} grupo(s) duplicado(s), {total_remover} registro(s) a remover.")

        if args.apply:
            for grupo in grupos_duplicados.values():
                mantido = escolher_mantido(grupo)
                for s in grupo:
                    if s.id != mantido.id:
                        db.delete(s)
            db.commit()
            print(f"{total_remover} registro(s) removido(s) do banco.")
        else:
            print("Modo dry-run (nada foi apagado). Rode novamente com --apply para remover de fato.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
