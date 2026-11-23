from typing import Dict, Any, List
from collections import defaultdict

class DeepAnalyticsEngine:
    """
    Bước 4: Phân tích chuyên sâu & Tìm nguyên nhân gốc rễ (Deep Analytics & Root-Cause)
    - Viết & chạy mã thống kê tự động
    - Phân tích đóng góp (Drill-down: cửa hàng, khung giờ)
    - Đối chiếu nguyên nhân ngoại cảnh / sự cố tồn kho POS
    """
    def analyze_cancellations(
        self, 
        clean_orders: List[Dict[str, Any]], 
        inventory_alerts: List[Dict[str, Any]], 
        limit: int = 5
    ) -> Dict[str, Any]:
        store_stats = defaultdict(lambda: {
            "store_name": "", 
            "region": "",
            "total_orders": 0, 
            "cancelled_orders": 0,
            "hourly_cancellations": defaultdict(int)
        })

        total_orders_region = len(clean_orders)
        total_cancels_region = 0

        for order in clean_orders:
            store_id = order["store_id"]
            store_stats[store_id]["store_name"] = order.get("store_name", store_id)
            store_stats[store_id]["region"] = order.get("region", "")
            store_stats[store_id]["total_orders"] += 1

            if order["status"] == "cancelled":
                total_cancels_region += 1
                store_stats[store_id]["cancelled_orders"] += 1
                hour = order.get("order_hour", 0)
                store_stats[store_id]["hourly_cancellations"][hour] += 1

        # 1. Tính toán KPI và xếp hạng
        store_ranking = []
        for s_id, data in store_stats.items():
            tot = data["total_orders"]
            can = data["cancelled_orders"]
            cancel_rate = (can / tot) if tot > 0 else 0.0
            store_ranking.append({
                "store_id": s_id,
                "store_name": data["store_name"],
                "region": data["region"],
                "total_orders": tot,
                "cancelled_orders": can,
                "cancellation_rate": round(cancel_rate, 4),
                "cancellation_rate_pct": round(cancel_rate * 100, 2),
                "hourly_cancellations": dict(data["hourly_cancellations"])
            })

        # Sắp xếp giảm dần theo tỷ lệ hủy
        store_ranking.sort(key=lambda x: x["cancellation_rate"], reverse=True)
        top_stores = store_ranking[:limit]

        avg_region_rate = (total_cancels_region / total_orders_region) if total_orders_region > 0 else 0.0

        # 2. Bóc tách nguyên nhân gốc rễ (Root Cause) cho cửa hàng Top 1
        root_cause_analysis = {}
        if top_stores:
            top_1 = top_stores[0]
            top_1_cancels = top_1["cancelled_orders"]
            
            # Phân tích theo khung giờ
            hourly_map = top_1["hourly_cancellations"]
            # Gom khung giờ cao điểm 17h-19h
            peak_cancels = sum(hourly_map.get(h, 0) for h in [17, 18, 19])
            peak_ratio = (peak_cancels / top_1_cancels) if top_1_cancels > 0 else 0.0

            # Đối chiếu với cảnh báo tồn kho (Inventory Alerts)
            relevant_alerts = [
                a for a in inventory_alerts 
                if a.get("store_id") == top_1["store_id"]
            ]

            alert_reasons = [a.get("alert_reason") for a in relevant_alerts]

            root_cause_analysis = {
                "worst_store_id": top_1["store_id"],
                "worst_store_name": top_1["store_name"],
                "cancellation_rate": top_1["cancellation_rate_pct"],
                "vs_average_ratio": round(top_1["cancellation_rate"] / avg_region_rate, 1) if avg_region_rate > 0 else 1.0,
                "peak_hours": "17h–19h",
                "peak_hour_cancellation_pct": round(peak_ratio * 100, 1),
                "correlated_inventory_alerts": alert_reasons,
                "identified_root_cause": (
                    f"{round(peak_ratio * 100, 1)}% đơn hủy tại {top_1['store_name']} tập trung vào khung giờ cao điểm (17h–19h). "
                    f"Nguyên nhân cốt lõi do lệch tồn kho thực tế và hệ thống POS chưa đồng bộ kịp, dẫn đến nhận đơn khi đã hết hàng."
                ) if alert_reasons else "Cần kiểm tra thêm nhật ký vận hành tại cửa hàng."
            }

        return {
            "overall_summary": {
                "total_orders": total_orders_region,
                "total_cancels": total_cancels_region,
                "average_cancellation_rate_pct": round(avg_region_rate * 100, 2)
            },
            "top_stores": top_stores,
            "root_cause_analysis": root_cause_analysis
        }

