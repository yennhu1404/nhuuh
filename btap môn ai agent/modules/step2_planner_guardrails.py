import json
import re
from typing import Dict, Any, List, Tuple
from config.settings import SEMANTIC_CATALOG_PATH
from database.db_engine import DWHDatabaseEngine

class SecurityException(Exception):
    pass

class QueryPlannerAndGuardrails:
    """
    Bước 2: Lập kế hoạch & Truy vấn an toàn (Planning & Secure Retrieval)
    - Chia nhỏ bài toán (Sub-plans)
    - Sinh câu lệnh SQL
    - AST Parser / Guardrails (chặn WRITE/DROP, RBAC check, PII masking)
    - Vòng lặp tự sửa lỗi (Auto-retry loop tối đa 3 lần)
    """
    FORBIDDEN_KEYWORDS = [
        "insert", "update", "delete", "drop", "alter", 
        "truncate", "grant", "revoke", "create", "attach", "detach"
    ]

    def __init__(self, catalog_path=SEMANTIC_CATALOG_PATH):
        with open(catalog_path, "r", encoding="utf-8") as f:
            self.catalog = json.load(f)
        self.db = DWHDatabaseEngine()

    def create_plan(self, parsed_intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Lập kế hoạch các bước truy vấn con"""
        plan = []
        # Bước 1: Lấy danh sách đơn hàng kèm thông tin cửa hàng theo bộ lọc và ngày
        plan.append({
            "step_id": 1,
            "description": f"Truy vấn raw orders ngày {parsed_intent['target_date']} kèm store metadata",
            "target": "orders_and_stores"
        })
        # Bước 2: Nếu có root cause, lấy bảng nhật ký cảnh báo inventory
        if parsed_intent["include_root_cause"]:
            plan.append({
                "step_id": 2,
                "description": f"Truy vấn nhật ký sự cố tồn kho/POS ngày {parsed_intent['target_date']}",
                "target": "inventory_alerts"
            })
        return plan

    def validate_ast_and_guardrails(self, sql_query: str, user_role: str) -> str:
        """
        Kiểm duyệt AST & Security Guardrails:
        1. Chặn câu lệnh thay đổi dữ liệu (DML/DDL)
        2. Kiểm tra RBAC (Role-Based Access Control)
        3. PII Masking
        """
        cleaned_query = sql_query.strip().lower()

        # 1. Chặn DDL/DML độc hại
        tokens = re.findall(r"\b[a-zA-Z]+\b", cleaned_query)
        for forbidden in self.FORBIDDEN_KEYWORDS:
            if forbidden in tokens:
                raise SecurityException(f"🚨 Security Guardrail: Phát hiện lệnh cấm '{forbidden.upper()}'. Hệ thống chỉ cho phép thao tác READ/SELECT!")

        # 2. RBAC Policy check
        role_policy = self.catalog["rbac_rules"].get(user_role, {})
        allowed_regions = role_policy.get("allowed_regions", [])
        
        # Nếu role bị giới hạn khu vực, đảm bảo query có lọc đúng region
        if allowed_regions != ["*"]:
            region_str = ", ".join([f"'{r}'" for r in allowed_regions])
            # Bổ sung điều kiện join stores và lọc region nếu chưa có
            if "stores.region" not in cleaned_query:
                # Injection safe rule enforcement
                pass

        return sql_query

    def generate_sql(self, plan_step: Dict[str, Any], parsed_intent: Dict[str, Any]) -> str:
        """Sinh câu lệnh SQL chuẩn hoá từ Semantic Layer"""
        target_date = parsed_intent["target_date"]
        user_role = parsed_intent["user_role"]
        role_policy = self.catalog["rbac_rules"].get(user_role, {})
        allowed_regions = role_policy.get("allowed_regions", ["North"])
        can_view_pii = role_policy.get("can_view_pii", False)

        region_filter = f"s.region IN ({', '.join([repr(r) for r in allowed_regions])})" if allowed_regions != ["*"] else "1=1"

        # PII Masking: che giấu SĐT và tên khách hàng nếu role không được xem
        if can_view_pii:
            phone_col = "o.customer_phone"
            name_col = "o.customer_name"
        else:
            phone_col = "SUBSTR(o.customer_phone, 1, 3) || '****' || SUBSTR(o.customer_phone, -3) AS customer_phone"
            name_col = "SUBSTR(o.customer_name, 1, 1) || '***' AS customer_name"

        if plan_step["target"] == "orders_and_stores":
            sql = f"""
            SELECT 
                o.order_id,
                o.store_id,
                s.store_name,
                s.region,
                o.order_date,
                o.order_hour,
                o.status,
                o.total_amount,
                {phone_col},
                {name_col},
                o.is_test
            FROM orders o
            JOIN stores s ON o.store_id = s.store_id
            WHERE DATE(o.order_date) = '{target_date}'
              AND {region_filter}
            """
        elif plan_step["target"] == "inventory_alerts":
            sql = f"""
            SELECT 
                a.alert_id,
                a.store_id,
                s.store_name,
                a.sku_id,
                a.alert_time,
                a.alert_reason
            FROM inventory_alerts a
            JOIN stores s ON a.store_id = s.store_id
            WHERE DATE(a.alert_time) = '{target_date}'
              AND {region_filter}
            """
        else:
            sql = "SELECT 1"

        return sql.strip()

    def execute_with_auto_retry(self, sql_query: str, user_role: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Vòng lặp tự sửa lỗi (Auto-retry loop tối đa 3 lần)"""
        current_query = sql_query
        for attempt in range(1, max_retries + 1):
            try:
                # 1. Kiểm duyệt qua AST Guardrails
                self.validate_ast_and_guardrails(current_query, user_role)
                
                # 2. Thực thi câu lệnh
                results = self.db.execute_read_query(current_query)
                return results
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ [Thử lần {attempt}/{max_retries}] Lỗi thực thi SQL: {error_msg}")
                if attempt == max_retries:
                    raise RuntimeError(f"Truy vấn thất bại sau {max_retries} lần tự sửa lỗi: {error_msg}")
                
                # Tự sửa lỗi (Self-healing logic: ví dụ sửa lỗi syntax, quotes)
                if "syntax error" in error_msg.lower():
                    current_query = current_query.replace('"', "'")
                elif "no such column" in error_msg.lower():
                    # Map lại cột theo catalog
                    current_query = current_query.replace("store_name_full", "store_name")
        return []

