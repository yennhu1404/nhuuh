import json
import datetime
from typing import Dict, Any, List
from config.settings import DATA_DIR

class DeliveryAndFeedbackLoop:
    """
    Bước 6: Phản hồi tương tác & Cảnh báo chủ động (Delivery & Human-in-the-loop)
    - Định dạng thông điệp đa kênh (Lark Suite Card, Slack Block Kit, Web UI)
    - Cảnh báo chủ động & Thẻ phê duyệt (Approval Card) khi vượt ngưỡng
    - Vòng lặp học hỏi (Feedback Loop vào Long-Term Memory / Vector DB)
    """
    def __init__(self, memory_file=DATA_DIR / "agent_memory.json"):
        self.memory_file = memory_file
        if not self.memory_file.exists():
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump({"feedback_history": [], "kpi_overrides": {}}, f)

    def build_delivery_payload(
        self, 
        narrative: str, 
        chart_url: str, 
        csv_url: str, 
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tạo payload hiển thị đa kênh kèm Approval Card nếu vượt ngưỡng"""
        top_store = analysis_result["top_stores"][0] if analysis_result.get("top_stores") else None
        is_risk_triggered = False
        approval_card = None

        # Kiểm tra ngưỡng rủi ro (> 15%)
        if top_store and top_store["cancellation_rate_pct"] >= 15.0:
            is_risk_triggered = True
            approval_card = {
                "card_type": "Proactive_Action_Approval",
                "severity": "CRITICAL",
                "alert_title": f"🚨 CẢNH BÁO: Tỷ lệ hủy đơn tại {top_store['store_name']} vượt ngưỡng ({top_store['cancellation_rate_pct']}%)",
                "actions": [
                    {
                        "action_id": "approve_sync_rate",
                        "label": "✅ Phê duyệt: Tăng tần suất đồng bộ POS lên 3 phút",
                        "payload": {"target_store": top_store["store_id"], "interval_min": 3}
                    },
                    {
                        "action_id": "request_explanation",
                        "label": "📝 Yêu cầu Quản lý cửa hàng giải trình",
                        "payload": {"target_store": top_store["store_id"], "deadline_hours": 4}
                    }
                ]
            }

        return {
            "channel_format": "Lark_Suite_Interactive_Card",
            "narrative_text": narrative,
            "attachments": {
                "chart_html_path": chart_url,
                "download_csv_path": csv_url
            },
            "proactive_alert": approval_card,
            "created_at": datetime.datetime.now().isoformat()
        }

    def record_user_feedback(self, query_id: str, feedback_type: str, comment: str = None, kpi_override: Dict[str, Any] = None):
        """Ghi nhận đánh giá người dùng vào bộ nhớ dài hạn để tự học"""
        with open(self.memory_file, "r", encoding="utf-8") as f:
            memory = json.load(f)

        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query_id": query_id,
            "feedback": feedback_type, # 'like', 'dislike', 'edit_definition'
            "comment": comment
        }
        memory["feedback_history"].append(record)

        if kpi_override:
            memory["kpi_overrides"].update(kpi_override)

        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

        print(f"🧠 [Feedback Loop] Đã lưu phản hồi vào bộ nhớ dài hạn của Agent.")

