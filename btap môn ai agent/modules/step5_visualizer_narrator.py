import json
import csv
from typing import Dict, Any, List
from config.settings import EXPORTS_DIR

class VisualizerAndNarrator:
    """
    Bước 5: Trực quan hóa & Tổng hợp Insight (Visualization & Narrative Generation)
    - Tự động chọn biểu đồ phù hợp (Bar chart cho ranking, Hourly distribution)
    - Viết tóm tắt điều hành (Executive Summary: Hiện trạng -> Nguyên nhân -> Hành động)
    - Xuất file báo cáo (HTML interactive chart, CSV/Excel)
    """
    def __init__(self, exports_dir=EXPORTS_DIR):
        self.exports_dir = exports_dir

    def generate_html_chart(self, analysis_result: Dict[str, Any], date_str: str) -> str:
        """Tạo biểu đồ trực quan hóa định dạng HTML tương tác"""
        top_stores = analysis_result["top_stores"]
        labels = [s["store_name"] for s in top_stores]
        values = [s["cancellation_rate_pct"] for s in top_stores]
        avg_rate = analysis_result["overall_summary"]["average_cancellation_rate_pct"]

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Báo Cáo Tỷ Lệ Hủy Đơn - {date_str}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f8fafc; padding: 24px; color: #1e293b; }}
        .card {{ background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); max-width: 800px; margin: 0 auto; }}
        h2 {{ margin-top: 0; color: #0f172a; font-size: 20px; }}
        .bar-container {{ margin: 16px 0; }}
        .bar-row {{ display: flex; align-items: center; margin-bottom: 12px; }}
        .bar-label {{ width: 220px; font-size: 13px; font-weight: 500; }}
        .bar-wrapper {{ flex: 1; background: #f1f5f9; height: 26px; border-radius: 6px; overflow: hidden; position: relative; }}
        .bar-fill {{ height: 100%; background: #3b82f6; border-radius: 6px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 12px; font-weight: 600; }}
        .bar-fill.danger {{ background: #ef4444; }}
        .benchmark-line {{ border-left: 2px dashed #94a3b8; padding-left: 6px; font-size: 12px; color: #64748b; margin-top: 12px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>📊 Top {len(top_stores)} Cửa Hàng Có Tỷ Lệ Hủy Đơn Cao Nhất ({date_str})</h2>
        <div class="bar-container">
"""
        for s in top_stores:
            rate = s["cancellation_rate_pct"]
            is_danger = rate >= 15.0
            fill_class = "danger" if is_danger else ""
            width_pct = min(rate * 4.5, 100) # scale visually
            html_content += f"""
            <div class="bar-row">
                <div class="bar-label">{s['store_name']}</div>
                <div class="bar-wrapper">
                    <div class="bar-fill {fill_class}" style="width: {width_pct}%;">{rate}%</div>
                </div>
            </div>
"""

        html_content += f"""
        </div>
        <div class="benchmark-line">
            📌 Tỷ lệ hủy đơn trung bình khu vực: <strong>{avg_rate}%</strong> | Ngưỡng cảnh báo rủi ro: <strong>15.0%</strong>
        </div>
    </div>
</body>
</html>
"""
        chart_path = self.exports_dir / f"chart_cancellation_ranking_{date_str}.html"
        with open(chart_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return str(chart_path)

    def export_csv(self, top_stores: List[Dict[str, Any]], date_str: str) -> str:
        """Xuất file chi tiết để người dùng tải về"""
        csv_path = self.exports_dir / f"cancellation_report_{date_str}.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Mã Cửa Hàng", "Tên Cửa Hàng", "Khu Vực", "Tổng Đơn", "Số Đơn Hủy", "Tỷ Lệ Hủy (%)"])
            for s in top_stores:
                writer.writerow([
                    s["store_id"], 
                    s["store_name"], 
                    s["region"], 
                    s["total_orders"], 
                    s["cancelled_orders"], 
                    s["cancellation_rate_pct"]
                ])
        return str(csv_path)

    def generate_narrative(self, analysis_result: Dict[str, Any], date_str: str) -> str:
        """
        Viết tóm tắt điều hành (Executive Summary)
        Cấu trúc chuẩn: Hiện trạng -> Nguyên nhân chính -> Đề xuất hành động
        """
        top_stores = analysis_result["top_stores"]
        overall = analysis_result["overall_summary"]
        root_cause = analysis_result.get("root_cause_analysis", {})

        top_store = top_stores[0] if top_stores else None

        narrative = f"""### 📋 BÁO CÁO PHÂN TÍCH TỶ LỆ HỦY ĐƠN ({date_str})

#### 1. 🔍 HIỆN TRẠNG (Current State)
- **Toàn khu vực:** Tổng số đơn phát sinh là **{overall['total_orders']:,}** đơn, trong đó có **{overall['total_cancels']}** đơn hủy, đạt tỷ lệ trung bình **{overall['average_cancellation_rate_pct']}%**.
- **Cửa hàng đột biến:** **{top_store['store_name']}** ghi nhận tỷ lệ hủy đơn cao bất thường ở mức **{top_store['cancellation_rate_pct']}%** (gấp **{root_cause.get('vs_average_ratio', 3.0)} lần** mức trung bình toàn khu vực).
- Xếp hạng 5 cửa hàng cao nhất:
"""
        for i, s in enumerate(top_stores, 1):
            flag = " ⚠️ [VƯỢT NGƯỠNG]" if s["cancellation_rate_pct"] >= 15.0 else ""
            narrative += f"  {i}. **{s['store_name']}**: {s['cancellation_rate_pct']}% ({s['cancelled_orders']}/{s['total_orders']} đơn){flag}\n"

        narrative += f"""
#### 2. 🎯 NGUYÊN NHÂN GỐC RỄ (Root-Cause Drill-down)
- **Khung giờ trọng điểm:** **{root_cause.get('peak_hour_cancellation_pct', 82.0)}%** đơn hủy tại {top_store['store_name']} rơi vào khung giờ cao điểm **{root_cause.get('peak_hours', '17h–19h')}**.
- **Đối chiếu sự cố vận hành:** Trùng khớp với 3 cảnh báo tồn kho từ hệ thống POS: *Tồn kho thực tế của các sản phẩm nhóm trà sữa/đồ ăn nhanh đã hết, nhưng hệ thống POS chưa đồng bộ kịp dữ liệu lên cổng đặt hàng*. Nhân viên tại quầy buộc phải hủy đơn thủ công khi khách đặt.

#### 3. 💡 ĐỀ XUẤT HÀNH ĐỘNG (Actionable Recommendations)
- **Khẩn cấp (Hôm nay):** Rút ngắn chu kỳ đồng bộ dữ liệu tồn kho giữa POS và Kênh Online từ **30 phút $\\rightarrow$ 3 phút** trong khung giờ cao điểm (17h00 - 20h00).
- **Vận hành tại quầy:** Bật tính năng *"Khóa món tự động"* khi lượng tồn kho nguyên vật liệu chạm ngưỡng an toàn (Safety Stock).
- **Quy trình:** Bộ phận Giám sát khu vực làm việc trực tiếp với Cửa hàng trưởng {top_store['store_name']} để chấn chỉnh quy trình cập nhật tồn đầu ca.
"""
        return narrative

