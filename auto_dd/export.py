import io
import json
from html import escape
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from .model import validate


def xlsx(data):
    data = validate(data)
    wb = Workbook()
    summary = wb.active
    summary.title = "Tables"
    summary.append(["Schema", "Table", "Description", "Columns"])
    columns = wb.create_sheet("Columns")
    columns.append(["Schema", "Table", "Column", "Type", "Nullable", "PK", "Default", "Description"])
    relations = wb.create_sheet("Relationships")
    relations.append(["Table", "Constraint", "Columns", "Target table", "Target columns"])
    for table in data["tables"]:
        summary.append([table["schema"], table["name"], table["description"], len(table["columns"])])
        for c in table["columns"]:
            columns.append([table["schema"], table["name"], c["name"], c["type"],
                            "YES" if c["nullable"] else "NO", "YES" if c["primary_key"] else "NO",
                            c["default"], c["description"]])
        for fk in table["foreign_keys"]:
            relations.append([table["id"], fk["name"], ", ".join(fk["columns"]),
                              fk["target_table"], ", ".join(fk["target_columns"])])
    for sheet in wb:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str):
                    # Store metadata literally, even when it resembles an Excel formula.
                    cell.value = cell.value[:32767]
                    cell.data_type = "s"
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        for cell in sheet[1]:
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = PatternFill("solid", fgColor="243B53")
        for index, col in enumerate(sheet.columns, 1):
            sheet.column_dimensions[col[0].column_letter].width = min(65, max(15, max(len(str(c.value or "")) for c in col)+2))
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def layout(data):
    positions = {}
    # Row spacing accounts for the tallest table; large catalogs never overlap by default.
    y = 40
    for index in range(0, len(data["tables"]), 3):
        row = data["tables"][index:index+3]
        for column, table in enumerate(row):
            positions[table["id"]] = table.get("position", {"x": 40 + column*360, "y": y})
        y += max(72+len(t["columns"])*26 for t in row)+80
    return positions


def svg(data):
    data = validate(data)
    positions = layout(data)
    width = max([1080]+[p["x"]+360 for p in positions.values()])
    height = max([400]+[positions[t["id"]]["y"]+100+len(t["columns"])*26 for t in data["tables"]])
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#f5f7fb"/>',
           '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#4569d4"/></marker></defs>']
    for table in data["tables"]:
        p = positions[table["id"]]
        for fk in table["foreign_keys"]:
            q = positions.get(fk["target_table"])
            if q:
                if table["id"] == fk["target_table"]:
                    path = f'M {p["x"]+300} {p["y"]+18} C {p["x"]+350} {p["y"]-40}, {p["x"]+350} {p["y"]+70}, {p["x"]+300} {p["y"]+60}'
                else:
                    path = f'M {p["x"]+300} {p["y"]+20} L {q["x"]} {q["y"]+20}'
                out.append(f'<path d="{path}" stroke="#4569d4" stroke-width="2" fill="none" marker-end="url(#arrow)"/><text x="{p["x"]+305}" y="{p["y"]+12}" font-size="11" fill="#4569d4">{escape(fk["name"])}</text>')
    for table in data["tables"]:
        p = positions[table["id"]]
        x, y = p["x"], p["y"]
        out.append(f'<g font-family="sans-serif"><rect x="{x}" y="{y}" width="300" height="{52+len(table["columns"])*26}" rx="8" fill="white" stroke="#ced8e5"/>')
        out.append(f'<text x="{x+12}" y="{y+22}" font-size="14" font-weight="bold">{escape(table["name"])}</text><text x="{x+12}" y="{y+40}" font-size="11" fill="#64748b">{escape(table["schema"])}</text>')
        for i, col in enumerate(table["columns"]):
            mark = "PK " if col["primary_key"] else ""
            out.append(f'<text x="{x+12}" y="{y+68+i*26}" font-size="12">{escape(mark+col["name"]+" : "+col["type"])}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "".join(out).encode()


def mermaid(data):
    data = validate(data)
    ids = {t["id"]: f"T{i}" for i, t in enumerate(data["tables"])}
    # Synthetic identifiers avoid executable Mermaid directives in imported names.
    out = ["erDiagram"]
    def label(value):
        return str(value).replace('"', "'").replace("\n", " ").replace("\r", " ").replace("\\", "/")
    for table in data["tables"]:
        out.append(f'    {ids[table["id"]]}["{label(table["id"])}"] {{')
        for i, col in enumerate(table["columns"]):
            out.append(f'        field c{i} {"PK" if col["primary_key"] else ""} "{label(col["name"]+": "+col["type"])}"')
        out.append("    }")
        for fk in table["foreign_keys"]:
            if fk["target_table"] in ids:
                out.append(f'    {ids[fk["target_table"]]} ||..o{{ {ids[table["id"]]} : "{label(fk["name"])}"')
    return "\n".join(out).encode()


def export(data, kind):
    data = validate(data)
    if kind == "json":
        return json.dumps(data, ensure_ascii=False, indent=2).encode()
    if kind == "xlsx":
        return xlsx(data)
    if kind == "svg":
        return svg(data)
    if kind == "mmd":
        return mermaid(data)
    raise ValueError("지원하지 않는 내보내기 형식입니다.")
