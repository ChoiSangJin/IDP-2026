"""Portable catalog contract shared by extraction, editing and exports."""
import copy
import json
from datetime import datetime, timezone


def catalog(source, tables):
    return validate({"version": 1, "source": source,
                     "generated_at": datetime.now(timezone.utc).isoformat(), "tables": tables})


def validate(data):
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("지원하는 카탈로그 형식은 version: 1 입니다.")
    result = copy.deepcopy(data)
    tables = result.get("tables")
    if not isinstance(tables, list) or len(tables) > 500:
        raise ValueError("tables 배열이 필요합니다. 최대 500개 테이블을 지원합니다.")
    ids = set()
    for table in tables:
        if not isinstance(table, dict):
            raise ValueError("테이블은 객체여야 합니다.")
        for field in ("id", "schema", "name"):
            require_text(table.get(field), field)
        if table["id"] in ids:
            raise ValueError("테이블 ID가 중복되었습니다.")
        ids.add(table["id"])
        table.setdefault("description", "")
        require_text(table["description"], "description", empty=True)
        columns = table.get("columns")
        if not isinstance(columns, list) or not 1 <= len(columns) <= 2000:
            raise ValueError("각 테이블에는 1~2000개 컬럼이 필요합니다.")
        names = set()
        for col in columns:
            if not isinstance(col, dict):
                raise ValueError("컬럼은 객체여야 합니다.")
            for field in ("name", "type"):
                require_text(col.get(field), field)
            if col["name"] in names:
                raise ValueError("컬럼 이름이 중복되었습니다.")
            names.add(col["name"])
            col.setdefault("nullable", True)
            col.setdefault("primary_key", False)
            col.setdefault("description", "")
            col.setdefault("default", None)
            for field in ("nullable", "primary_key"):
                if not isinstance(col[field], bool):
                    raise ValueError(f"{field}는 boolean이어야 합니다.")
            require_text(col["description"], "description", empty=True)
            if col["default"] is not None:
                require_text(col["default"], "default", empty=True)
        table.setdefault("foreign_keys", [])
        if not isinstance(table["foreign_keys"], list) or len(table["foreign_keys"]) > 2000:
            raise ValueError("foreign_keys 배열이 필요합니다.")
        position = table.get("position")
        if position is not None and (not isinstance(position, dict) or any(
            isinstance(position.get(k), bool) or not isinstance(position.get(k), (int, float))
            or not 0 <= position[k] <= 100000 for k in ("x", "y")
        )):
            raise ValueError("ERD 좌표는 0~100000 범위의 숫자여야 합니다.")
    by_id = {t["id"]: t for t in tables}
    for table in tables:
        for fk in table["foreign_keys"]:
            if not isinstance(fk, dict):
                raise ValueError("외래키는 객체여야 합니다.")
            require_text(fk.get("name"), "foreign key name")
            require_text(fk.get("target_table"), "target_table")
            for field in ("columns", "target_columns"):
                if not isinstance(fk.get(field), list) or not fk[field]:
                    raise ValueError("외래키 컬럼 배열이 필요합니다.")
                for name in fk[field]:
                    require_text(name, field)
            if len(fk["columns"]) != len(fk["target_columns"]):
                raise ValueError("외래키의 양쪽 컬럼 개수가 달라요.")
            if any(c not in {c["name"] for c in table["columns"]} for c in fk["columns"]):
                raise ValueError("외래키 원본 컬럼이 없습니다.")
            target = by_id.get(fk["target_table"])
            # A filtered extraction may retain a relationship to an excluded table.
            if target and any(c not in {c["name"] for c in target["columns"]} for c in fk["target_columns"]):
                raise ValueError("외래키 대상 컬럼이 없습니다.")
    return result


def require_text(value, field, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > 10000:
        raise ValueError(f"{field}: 유효한 문자열이 필요합니다 (최대 10000자).")


def load(path):
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))
