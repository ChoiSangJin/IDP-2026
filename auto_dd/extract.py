"""Metadata only; never select application rows or persist connection secrets."""
from .model import catalog


def postgres(dsn, schemas=None):
    import psycopg
    schemas = schemas or ["public"]
    with psycopg.connect(dsn, connect_timeout=10) as conn:
        conn.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '30s'")
        rows = conn.execute("""
            SELECT n.nspname, c.relname, obj_description(c.oid, 'pg_class'),
                   a.attname, format_type(a.atttypid, a.atttypmod),
                   NOT a.attnotnull, pg_get_expr(d.adbin, d.adrelid),
                   col_description(c.oid, a.attnum),
                   EXISTS (SELECT 1 FROM pg_constraint pk
                           WHERE pk.conrelid=c.oid AND pk.contype='p'
                           AND a.attnum=ANY(pk.conkey))
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_attribute a ON a.attrelid=c.oid
            LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
            WHERE n.nspname=ANY(%s) AND c.relkind IN ('r','p','v','m','f')
              AND a.attnum>0 AND NOT a.attisdropped
            ORDER BY n.nspname,c.relname,a.attnum
        """, (schemas,)).fetchall()
        tables = {}
        for schema, name, description, col, dtype, nullable, default, comment, pk in rows:
            key = f"{schema}.{name}"
            table = tables.setdefault(key, {"id": key, "schema": schema, "name": name,
                                            "description": description or "", "columns": [], "foreign_keys": []})
            table["columns"].append({"name": col, "type": dtype, "nullable": nullable,
                                      "default": default, "description": comment or "", "primary_key": pk})
        relationships = conn.execute("""
            SELECT ns.nspname, src.relname, con.conname, nt.nspname, dst.relname,
                   array_agg(sa.attname ORDER BY k.ord), array_agg(ta.attname ORDER BY k.ord)
            FROM pg_constraint con
            JOIN pg_class src ON src.oid=con.conrelid JOIN pg_namespace ns ON ns.oid=src.relnamespace
            JOIN pg_class dst ON dst.oid=con.confrelid JOIN pg_namespace nt ON nt.oid=dst.relnamespace
            JOIN LATERAL unnest(con.conkey,con.confkey) WITH ORDINALITY k(s,t,ord) ON true
            JOIN pg_attribute sa ON sa.attrelid=src.oid AND sa.attnum=k.s
            JOIN pg_attribute ta ON ta.attrelid=dst.oid AND ta.attnum=k.t
            WHERE con.contype='f' AND ns.nspname=ANY(%s)
            GROUP BY ns.nspname,src.relname,con.conname,nt.nspname,dst.relname
            ORDER BY ns.nspname,src.relname,con.conname
        """, (schemas,)).fetchall()
        for schema, name, constraint, target_schema, target_name, cols, target_cols in relationships:
            if f"{schema}.{name}" in tables:
                tables[f"{schema}.{name}"]["foreign_keys"].append({
                    "name": constraint, "columns": cols, "target_table": f"{target_schema}.{target_name}",
                    "target_columns": target_cols})
    return catalog("postgresql", list(tables.values()))


def bigquery(project, dataset):
    from google.cloud import bigquery as bq
    if not project or not dataset or "." in dataset:
        raise ValueError("프로젝트와 단일 데이터셋 이름이 필요합니다.")
    client = bq.Client(project=project)
    try:
        return bigquery_catalog(client, project, dataset)
    finally:
        client.close()


def bigquery_catalog(client, project, dataset):
    tables = []
    for item in client.list_tables(f"{project}.{dataset}", timeout=30):
        table = client.get_table(item.reference, timeout=30)
        cols = []

        def walk(fields, prefix=""):
            for field in fields:
                name = prefix + field.name
                cols.append({"name": name, "type": field.field_type + ("[]" if field.mode == "REPEATED" else ""),
                             "nullable": field.mode != "REQUIRED", "primary_key": False,
                             "default": field.default_value_expression, "description": field.description or ""})
                if field.fields:
                    walk(field.fields, name + ".")

        walk(table.schema)
        constraints = table.table_constraints
        fks = []
        if constraints:
            pk = set(constraints.primary_key.columns if constraints.primary_key else [])
            for col in cols:
                col["primary_key"] = col["name"] in pk
            for fk in constraints.foreign_keys or []:
                target = fk.referenced_table
                fks.append({"name": fk.name or f"fk_{len(fks)+1}",
                            "columns": [c.referencing_column for c in fk.column_references],
                            "target_table": f"{target.project}.{target.dataset_id}.{target.table_id}",
                            "target_columns": [c.referenced_column for c in fk.column_references]})
        tables.append({"id": f"{project}.{dataset}.{table.table_id}", "schema": f"{project}.{dataset}",
                       "name": table.table_id, "description": table.description or "",
                       "columns": cols, "foreign_keys": fks})
    return catalog("bigquery", tables)
