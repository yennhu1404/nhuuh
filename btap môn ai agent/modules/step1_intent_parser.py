import json
import re
import datetime
from typing import Dict, Any, List
from config.settings import SEMANTIC_CATALOG_PATH

class IntentParser:
    """
    Bước 1: Tiếp nhận & Hiểu ý định (Intent & Context Parsing)
    - Nhận input từ Chatbox, File (Excel/CSV), Cronjob
    - Phân tách thực thể (Entity Extraction: time, region, metric, dimension)
    - Đối chiếu Semantic Layer / Data Catalog
    """
    def __init__(self, catalog_path=SEMANTIC_CATALOG_PATH):
        with open(catalog_path, "r", encoding="utf-8") as f:
            self.catalog = json.load(f)

    def parse(self, user_query: str, trigger_source: str = "chat_box", context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        user_role = context.get("user_role", "Manager_Region_North")
        
        query_lower = user_query.lower()

        # 1. Trích xuất chỉ số KPI (Metric)
        target_metric = "cancellation_rate" # default fallback
        if "hủy" in query_lower or "cancel" in query_lower:
            target_metric = "cancellation_rate"
        elif "doanh thu" in query_lower or "revenue" in query_lower:
            target_metric = "revenue"

        metric_meta = self.catalog["metrics"].get(target_metric, {})

        # 2. Trích xuất thời gian (Time Entity)
        time_filter = "yesterday"
        if "hôm qua" in query_lower or "yesterday" in query_lower:
            time_filter = "yesterday"
            target_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        elif "hôm nay" in query_lower or "today" in query_lower:
            time_filter = "today"
            target_date = datetime.date.today().isoformat()
        else:
            target_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

        # 3. Trích xuất chiều phân tích (Dimension & Limit)
        dimension = "store_id"
        limit = 5
        match_top = re.search(r"top\s*(\d+)", query_lower)
        if match_top:
            limit = int(match_top.group(1))

        # 4. Trích xuất yêu cầu nguyên nhân (Root-cause intent)
        include_root_cause = any(w in query_lower for w in ["nguyên nhân", "tại sao", "lý do", "root cause", "bóc tách"])

        # 5. Semantic Mapping
        relevant_tables = ["orders", "stores"]
        if include_root_cause:
            relevant_tables.append("inventory_alerts")

        parsed_intent = {
            "trigger_source": trigger_source,
            "raw_query": user_query,
            "user_role": user_role,
            "metric": target_metric,
            "metric_formula": metric_meta.get("formula"),
            "required_filters": metric_meta.get("required_filters", []),
            "time_filter": time_filter,
            "target_date": target_date,
            "dimension": dimension,
            "limit": limit,
            "include_root_cause": include_root_cause,
            "semantic_tables": relevant_tables
        }
        return parsed_intent

