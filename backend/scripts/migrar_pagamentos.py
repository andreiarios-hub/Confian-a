"""Migração: adiciona as colunas de controle de pagamento de efetivos.

`Base.metadata.create_all` (rodado no startup da API) só cria tabelas que
ainda não existem — não altera tabelas já existentes. Como a tabela
`ordens_servico` já existe em produção (Neon), as novas colunas usadas pela
aba "Custo de Efetivos e Adicionais" precisam ser adicionadas manualmente:

  - pagamento_efetivos_status (enum PENDENTE/PAGO, default PENDENTE)
  - pagamento_efetivos_data (data, opcional)

O campo `custos_adicionais` não precisa de migração de schema — é uma coluna
JSON já existente; os novos campos "status" e "data_pagamento" de cada item
simplesmente passam a ser gravados dentro do JSON a partir de agora (itens
antigos sem esses campos são tratados como PENDENTE pelo frontend/backend).

Uso (a partir da pasta backend/):
    python scripts/migrar_pagamentos.py

Idempotente: rodar mais de uma vez não dá erro (verifica se a coluna já
existe antes de tentar criar).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402

from app.database import DATABASE_URL, engine  # noqa: E402


def main():
    print(f"Conectando em: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    inspector = inspect(engine)
    colunas_existentes = {c["name"] for c in inspector.get_columns("ordens_servico")}
    dialeto = engine.dialect.name

    with engine.begin() as conn:
        if dialeto == "postgresql":
            conn.execute(
                text(
                    "DO $$ BEGIN "
                    "CREATE TYPE statuspagamento AS ENUM ('PENDENTE', 'PAGO'); "
                    "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
                )
            )

        if "pagamento_efetivos_status" not in colunas_existentes:
            if dialeto == "postgresql":
                conn.execute(
                    text(
                        "ALTER TABLE ordens_servico "
                        "ADD COLUMN pagamento_efetivos_status statuspagamento "
                        "NOT NULL DEFAULT 'PENDENTE'"
                    )
                )
            else:
                conn.execute(
                    text(
                        "ALTER TABLE ordens_servico "
                        "ADD COLUMN pagamento_efetivos_status VARCHAR(20) "
                        "NOT NULL DEFAULT 'PENDENTE'"
                    )
                )
            print("Coluna pagamento_efetivos_status criada.")
        else:
            print("Coluna pagamento_efetivos_status já existe — pulando.")

        if "pagamento_efetivos_data" not in colunas_existentes:
            conn.execute(text("ALTER TABLE ordens_servico ADD COLUMN pagamento_efetivos_data DATE"))
            print("Coluna pagamento_efetivos_data criada.")
        else:
            print("Coluna pagamento_efetivos_data já existe — pulando.")

    print("Migração concluída.")


if __name__ == "__main__":
    main()
