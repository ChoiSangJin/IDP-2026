from .model import catalog


def sample():
    def col(name, kind, description, pk=False, nullable=False):
        return {"name": name, "type": kind, "description": description, "primary_key": pk, "nullable": nullable}
    return catalog("sample", [
        {"id": "public.customers", "schema": "public", "name": "customers", "description": "고객 기본 정보",
         "columns": [col("id", "bigint", "고객 식별자", True), col("name", "varchar(100)", "고객 이름"),
                     col("email", "varchar(255)", "이메일", nullable=True)]},
        {"id": "public.orders", "schema": "public", "name": "orders", "description": "고객 주문 내역",
         "columns": [col("id", "bigint", "주문 식별자", True), col("customer_id", "bigint", "고객 식별자"),
                     col("ordered_at", "timestamptz", "주문 일시"), col("total", "numeric(12,2)", "주문 금액")],
         "foreign_keys": [{"name": "orders_customer_fk", "columns": ["customer_id"],
                           "target_table": "public.customers", "target_columns": ["id"]}]},
        {"id": "public.order_items", "schema": "public", "name": "order_items", "description": "주문별 상품",
         "columns": [col("order_id", "bigint", "주문 식별자", True), col("line_no", "integer", "주문 행 번호", True),
                     col("product_name", "varchar(200)", "상품 이름"), col("quantity", "integer", "수량")],
         "foreign_keys": [{"name": "items_order_fk", "columns": ["order_id"],
                           "target_table": "public.orders", "target_columns": ["id"]}]},
    ])
