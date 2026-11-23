from database.seed_data import seed_enterprise_dwh
from agent import EnterpriseAnalyticsAgent

def main():
    print("======================================================================")
    print("DEMO CASE: BÀI TẬP MÔN AI AGENT - ENTERPRISE DATA ANALYTICS AGENT")
    print("======================================================================")

    # 1. Khởi tạo & nạp dữ liệu mẫu vào Data Warehouse
    print("\n📦 Đang nạp dữ liệu vào Database mẫu...")
    seed_enterprise_dwh()

    # 2. Khởi tạo Agent
    agent = EnterpriseAnalyticsAgent()

    # 3. Kịch bản chạy thực tế theo đúng đề bài:
    # Người dùng: Manager_Region_North
    # Câu hỏi: "Kiểm tra giúp tôi top 5 cửa hàng có tỷ lệ hủy đơn cao nhất hôm qua và nguyên nhân."
    user_query = "Kiểm tra giúp tôi top 5 cửa hàng có tỷ lệ hủy đơn cao nhất hôm qua và nguyên nhân."
    
    result = agent.run(
        user_query=user_query,
        user_role="Manager_Region_North",
        trigger="Lark_Suite_Chat"
    )

    # 4. In trực tiếp phần kết quả cuối cùng gửi người dùng
    print("\n" + "#"*70)
    print("📬 KẾT QUẢ HIỂN THỊ TRÊN GIAO DIỆN CHAT:")
    print("#"*70)
    print(result["narrative"])

    # 5. Mô phỏng người dùng đánh giá phản hồi (Step 6 Feedback Loop)
    print("\n👍 [Feedback Loop Demo] Người dùng đánh giá 'Hài lòng' và đồng ý phê duyệt:")
    agent.step6_delivery.record_user_feedback(
        query_id=result["query_id"],
        feedback_type="like",
        comment="Phân tích rất chuẩn, Store #04 đã xảy ra tình trạng tương tự tuần trước."
    )

if __name__ == "__main__":
    main()

