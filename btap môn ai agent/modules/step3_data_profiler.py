import json
import datetime
from typing import Dict, Any, List, Tuple
from config.settings import QUARANTINE_DIR

class DataProfilerAndQuarantine:
    """
    Bước 3: Làm sạch & Kiểm định chất lượng dữ liệu (Data Profiling & Quarantine)
    - Phát hiện bất thường (Anomaly Detection: NULL ID, âm tiền, test order, duplicate)
    - Cách ly dữ liệu lỗi (Quarantine sang file/bảng riêng)
    - Trả về tập dữ liệu sạch (Clean Data)
    """
    def __init__(self, quarantine_dir=QUARANTINE_DIR):
        self.quarantine_dir = quarantine_dir

    def profile_and_clean(self, raw_orders: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        clean_orders = []
        quarantine_records = []
        
        seen_order_ids = set()
        test_orders_count = 0
        negative_rev_count = 0
        missing_store_count = 0
        duplicate_count = 0

        for row in raw_orders:
            order_id = row.get("order_id")
            store_id = row.get("store_id")
            total_amount = row.get("total_amount", 0.0)
            is_test = row.get("is_test", 0)

            quarantine_reasons = []

            # 1. Phát hiện đơn test nội bộ
            if is_test == 1:
                quarantine_reasons.append("INTERNAL_TEST_ORDER (is_test=1)")
                test_orders_count += 1

            # 2. Phát hiện doanh thu âm
            if total_amount < 0:
                quarantine_reasons.append(f"NEGATIVE_REVENUE ({total_amount})")
                negative_rev_count += 1

            # 3. Phát hiện thiếu thông tin cửa hàng
            if not store_id or store_id == "None":
                quarantine_reasons.append("MISSING_STORE_ID (NULL)")
                missing_store_count += 1

            # 4. Phát hiện trùng lặp mã đơn
            if order_id in seen_order_ids:
                quarantine_reasons.append(f"DUPLICATE_ORDER_ID ({order_id})")
                duplicate_count += 1
            else:
                seen_order_ids.add(order_id)

            # Phân luồng dữ liệu
            if quarantine_reasons:
                quarantine_row = dict(row)
                quarantine_row["quarantine_reasons"] = quarantine_reasons
                quarantine_row["quarantined_at"] = datetime.datetime.now().isoformat()
                quarantine_records.append(quarantine_row)
            else:
                clean_orders.append(row)

        # Lưu dữ liệu cách ly vào thư mục data_quarantine
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_file = self.quarantine_dir / f"quarantined_orders_{timestamp}.json"
        with open(quarantine_file, "w", encoding="utf-8") as f:
            json.dump(quarantine_records, f, ensure_ascii=False, indent=2)

        profiling_summary = {
            "total_raw_records": len(raw_orders),
            "clean_records_count": len(clean_orders),
            "quarantined_count": len(quarantine_records),
            "quarantine_file": str(quarantine_file),
            "details": {
                "internal_test_orders_removed": test_orders_count,
                "negative_revenue_records": negative_rev_count,
                "missing_store_records": missing_store_count,
                "duplicate_order_records": duplicate_count
            }
        }

        return clean_orders, profiling_summary

