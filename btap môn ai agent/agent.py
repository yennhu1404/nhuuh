import uuid
import json
from typing import Dict, Any

from modules.step1_intent_parser import IntentParser
from modules.step2_planner_guardrails import QueryPlannerAndGuardrails
from modules.step3_data_profiler import DataProfilerAndQuarantine
from modules.step4_deep_analytics import DeepAnalyticsEngine
from modules.step5_visualizer_narrator import VisualizerAndNarrator
from modules.step6_delivery_feedback import DeliveryAndFeedbackLoop

class EnterpriseAnalyticsAgent:
    """
    Master Enterprise AI Agent Orchestrator
    Điều phối toàn bộ quy trình 6 bước phân tích dữ liệu chuyên sâu
    """
    def __init__(self):
        print("🤖 [Agent Init] Khởi tạo các hệ thống con...")
        self.step1_parser = IntentParser()
        self.step2_planner = QueryPlannerAndGuardrails()
        self.step3_profiler = DataProfilerAndQuarantine()
        self.step4_analytics = DeepAnalyticsEngine()
        self.step5_viz_narrator = VisualizerAndNarrator()
        self.step6_delivery = DeliveryAndFeedbackLoop()
        print("✅ [Agent Init] Sẵn sàng nhận lệnh.")

    def run(self, user_query: str, user_role: str = "Manager_Region_North", trigger: str = "chat_box") -> Dict[str, Any]:
        query_id = f"QRY_{uuid.uuid4().hex[:8]}"
        print("\n" + "="*70)
        print(f"🚀 [BẮT ĐẦU PHIÊN XỬ LÝ: {query_id}]")
        print(f"👤 Người dùng: {user_role} | Nguồn: {trigger}")
        print(f"💬 Yêu cầu: \"{user_query}\"")
        print("="*70)

        # ---------------------------------------------------------
        # BƯỚC 1: TIẾP NHẬN & HIỂU Ý ĐỊNH
        # ---------------------------------------------------------
        print("\n▶️ [BƯỚC 1] Tiếp nhận & Phân tách thực thể (Intent & Context Parsing)...")
        parsed_intent = self.step1_parser.parse(
            user_query, 
            trigger_source=trigger, 
            context={"user_role": user_role}
        )
        print(f"   - Chỉ số nhận diện: {parsed_intent['metric']} ({parsed_intent['metric_formula']})")
        print(f"   - Mốc thời gian: {parsed_intent['time_filter']} -> {parsed_intent['target_date']}")
        print(f"   - Bóc tách nguyên nhân: {parsed_intent['include_root_cause']}")
        print(f"   - Bảng liên quan: {parsed_intent['semantic_tables']}")

        # ---------------------------------------------------------
        # BƯỚC 2: LẬP KẾ HOẠCH & TRUY VẤN AN TOÀN
        # ---------------------------------------------------------
        print("\n▶️ [BƯỚC 2] Lập kế hoạch & Thực thi truy vấn qua Guardrails...")
        plan = self.step2_planner.create_plan(parsed_intent)
        raw_orders = []
        inventory_alerts = []

        for step in plan:
            print(f"   * Kế hoạch con {step['step_id']}: {step['description']}")
            sql_query = self.step2_planner.generate_sql(step, parsed_intent)
            print(f"     [Generated SQL]:\n     {sql_query.replace(chr(10), chr(10) + '     ')}")
            
            # Thực thi kèm AST Guardrail & Auto-Retry Loop
            step_results = self.step2_planner.execute_with_auto_retry(sql_query, user_role)
            print(f"     -> Trả về {len(step_results)} bản ghi.")
            
            if step["target"] == "orders_and_stores":
                raw_orders = step_results
            elif step["target"] == "inventory_alerts":
                inventory_alerts = step_results

        # ---------------------------------------------------------
        # BƯỚC 3: LÀM SẠCH & KIỂM ĐỊNH CHẤT LƯỢNG DỮ LIỆU
        # ---------------------------------------------------------
        print("\n▶️ [BƯỚC 3] Làm sạch & Kiểm định chất lượng dữ liệu (Data Profiling & Quarantine)...")
        clean_orders, profile_report = self.step3_profiler.profile_and_clean(raw_orders)
        print(f"   - Tổng bản ghi thô: {profile_report['total_raw_records']}")
        print(f"   - Bản ghi sạch đạt chuẩn: {profile_report['clean_records_count']}")
        print(f"   - Bản ghi lỗi đã cách ly: {profile_report['quarantined_count']}")
        print(f"     + Đơn test nội bộ (is_test=1) loại bỏ: {profile_report['details']['internal_test_orders_removed']}")
        print(f"     + Doanh thu âm: {profile_report['details']['negative_revenue_records']}")
        print(f"     + Thiếu mã cửa hàng: {profile_report['details']['missing_store_records']}")
        print(f"   - File cách ly dữ liệu: {profile_report['quarantine_file']}")

        # ---------------------------------------------------------
        # BƯỚC 4: PHÂN TÍCH CHUYÊN SÂU & TÌM NGUYÊN NHÂN GỐC RỄ
        # ---------------------------------------------------------
        print("\n▶️ [BƯỚC 4] Phân tích chuyên sâu & Drill-down tìm nguyên nhân gốc rễ...")
        analysis_result = self.step4_analytics.analyze_cancellations(
            clean_orders, 
            inventory_alerts, 
            limit=parsed_intent["limit"]
        )
        worst_store = analysis_result["top_stores"][0]
        print(f"   - Tỷ lệ hủy trung bình khu vực: {analysis_result['overall_summary']['average_cancellation_rate_pct']}%")
        print(f"   - Cửa hàng tỷ lệ hủy cao nhất: {worst_store['store_name']} ({worst_store['cancellation_rate_pct']}%)")
        print(f"   - Root Cause: {analysis_result['root_cause_analysis'].get('identified_root_cause')}")

        # ---------------------------------------------------------
        # BƯỚC 5: TRỰC QUAN HÓA & TỔNG HỢP INSIGHT
        # ---------------------------------------------------------
        print("\n▶️ [BƯỚC 5] Trực quan hóa & Sinh báo cáo tóm tắt điều hành...")
        target_date = parsed_intent["target_date"]
        chart_file = self.step5_viz_narrator.generate_html_chart(analysis_result, target_date)
        csv_file = self.step5_viz_narrator.export_csv(analysis_result["top_stores"], target_date)
        narrative = self.step5_viz_narrator.generate_narrative(analysis_result, target_date)
        print(f"   - Biểu đồ tương tác đã tạo: {chart_file}")
        print(f"   - File dữ liệu CSV: {csv_file}")

        # ---------------------------------------------------------
        # BƯỚC 6: PHẢN HỒI TƯƠNG TÁC & CẢNH BÁO CHỦ ĐỘNG
        # ---------------------------------------------------------
        print("\n▶️ [BƯỚC 6] Đóng gói phản hồi đa kênh & Cảnh báo chủ động (HITL)...")
        delivery_payload = self.step6_delivery.build_delivery_payload(
            narrative, 
            chart_file, 
            csv_file, 
            analysis_result
        )

        if delivery_payload.get("proactive_alert"):
            alert = delivery_payload["proactive_alert"]
            print(f"   🚨 {alert['alert_title']}")
            print(f"   🔘 Kèm 2 nút phê duyệt hành động cho Quản lý:")
            for act in alert["actions"]:
                print(f"      [{act['label']}]")

        print("\n" + "="*70)
        print("✅ [HOÀN THÀNH PHIÊN XỬ LÝ]")
        print("="*70)

        return {
            "query_id": query_id,
            "parsed_intent": parsed_intent,
            "profiling_summary": profile_report,
            "analysis_result": analysis_result,
            "narrative": narrative,
            "delivery_payload": delivery_payload
        }

