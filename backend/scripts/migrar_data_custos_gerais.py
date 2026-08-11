"""Migração: garante a tabela custos_gerais e a coluna "data" nela.

Se o deploy anterior já criou a tabela `custos_gerais` (via
Base.metadata.create_all) antes da coluna `data` existir no modelo, essa
coluna fica faltando — create_all só cria tabelas novas, não altera as já
existentes. Este script:

  1. Cria a tabela custos_gerais se ainda não existir (com o schema atual,
     já incluindo a coluna "data").
  2. Se a tabela já existir sem a coluna "data", adiciona a coluna e
     preenche os registros antigos com a data de criação (created_at).

Uso (a partir da pasta backend/):
    python scripts/migrar_data_custos_gerais.py

Idempotente: pode rodar mais de uma vez sem erro.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402

from app.database import Base, DATABASE_URL, engine  # noqa: E402
from app import models  # noqa: F401,E402  (garante que CustoGeral está registrado em Base.metadata)


def main():
    print(f"Conectando em: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if "custos_gerais" not in inspector.get_table_names():
        print("Tabela custos_gerais não foi criada — verifique a conexão.")
        return

    colunas_existentes = {c["name"] for c in inspector.get_columns("custos_gerais")}
    dialeto = engine.dialect.name

    with engine.begin() as conn:
        if "data" not in colunas_existentes:
            conn.execute(text("ALTER TABLE custos_gerais ADD COLUMN data DATE"))
            if dialeto == "postgresql":
                conn.execute(text("UPDATE custos_gerais SET data = created_at::date WHERE data IS NULL"))
            else:
                conn.execute(text("UPDATE custos_gerais SET data = date(created_at) WHERE data IS NULL"))
            print("Coluna 'data' criada e preenchida a partir de created_at.")
        else:
            print("Coluna 'data' já existe — pulando.")

    print("Migração concluída.")


if __name__ == "__main__":
    main()
