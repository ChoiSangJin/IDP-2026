import json
import os
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock
import pytest
from google.cloud import bigquery
from google.cloud.bigquery.table import TableConstraints, PrimaryKey, ForeignKey, ColumnReference
from auto_dd.extract import bigquery_catalog, postgres
from auto_dd.ai import describe
from auto_dd.sample import sample


def test_bigquery_sdk_nested_fields_and_constraints():
    table = bigquery.Table("project.dataset.orders", schema=[
        bigquery.SchemaField("id", "INTEGER", mode="REQUIRED", description="주문 ID"),
        bigquery.SchemaField("customer_id", "INTEGER"),
        bigquery.SchemaField("items", "RECORD", mode="REPEATED", fields=[bigquery.SchemaField("name", "STRING")]),
    ])
    table.table_constraints = TableConstraints(
        primary_key=PrimaryKey(["id"]),
        foreign_keys=[ForeignKey(
            "customer_fk", bigquery.TableReference.from_string("project.dataset.customers"),
            [ColumnReference("customer_id", "id")])])
    client = Mock()
    client.list_tables.return_value = [SimpleNamespace(reference=table.reference)]
    client.get_table.return_value = table
    data = bigquery_catalog(client, "project", "dataset")
    result = data["tables"][0]
    assert [c["name"] for c in result["columns"]] == ["id", "customer_id", "items", "items.name"]
    assert result["columns"][0]["primary_key"]
    assert result["columns"][2]["type"] == "RECORD[]"
    assert result["foreign_keys"][0]["target_table"] == "project.dataset.customers"


def test_local_ai_fills_empty_descriptions_only(monkeypatch):
    result = {"response": json.dumps({"description": "AI 제안", "columns": {"name": "고객 이름 제안"}})}
    opener = MagicMock()
    opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(result).encode()
    monkeypatch.setattr("urllib.request.build_opener", lambda *args: opener)
    data = sample()
    data["tables"] = data["tables"][:1]
    data["tables"][0]["columns"][1]["description"] = ""
    generated = describe(data)
    assert generated["tables"][0]["description"] == "고객 기본 정보"
    assert generated["tables"][0]["columns"][1]["description"] == "고객 이름 제안"
    assert data["tables"][0]["columns"][1]["description"] == ""
    req = opener.open.call_args.args[0]
    assert req.full_url == "http://127.0.0.1:11434/api/generate"
    assert "password" not in req.data.decode()


@pytest.mark.skipif(not os.environ.get("AUTO_DD_TEST_PG_DSN"), reason="실제 PostgreSQL 연결에는 AUTO_DD_TEST_PG_DSN이 필요합니다")
def test_postgres_live_composite_keys_comments_and_views():
    import psycopg
    dsn = os.environ["AUTO_DD_TEST_PG_DSN"]
    schema = "auto_dd_test"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(f"CREATE SCHEMA {schema}")
        try:
            conn.execute(f"CREATE TABLE {schema}.parent (a integer, b integer, PRIMARY KEY(a,b))")
            conn.execute(f"CREATE TABLE {schema}.child (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, a integer, b integer, amount numeric(12,2) DEFAULT 0, CONSTRAINT composite_fk FOREIGN KEY(a,b) REFERENCES {schema}.parent(a,b))")
            conn.execute(f"COMMENT ON TABLE {schema}.child IS '한글 테이블 설명'")
            conn.execute(f"COMMENT ON COLUMN {schema}.child.amount IS '금액'")
            conn.execute(f"CREATE VIEW {schema}.child_view AS SELECT amount FROM {schema}.child")
            data = postgres(dsn, [schema])
            tables = {t["name"]: t for t in data["tables"]}
            assert set(tables) == {"parent", "child", "child_view"}
            assert tables["child"]["description"] == "한글 테이블 설명"
            fk = tables["child"]["foreign_keys"][0]
            assert fk["columns"] == ["a", "b"] and fk["target_columns"] == ["a", "b"]
            amount = next(c for c in tables["child"]["columns"] if c["name"] == "amount")
            assert amount["type"] == "numeric(12,2)" and amount["description"] == "금액"
            assert amount["default"] is not None
            assert sum(c["primary_key"] for c in tables["parent"]["columns"]) == 2
            # Extraction never changes the application schema or populates data.
            assert conn.execute(f"SELECT count(*) FROM {schema}.child").fetchone()[0] == 0
        finally:
            conn.execute(f"DROP SCHEMA {schema} CASCADE")
