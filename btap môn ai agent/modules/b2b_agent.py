import re
import json
import datetime
from modules.b2b_catalog import OFFICIAL_CATALOG, SALES_REPRESENTATIVES, DISCOUNT_APPROVAL_POLICY

class B2BOpportunityOrchestrator:
    """
    Hệ thống AI Agent Orchestrator xử lý cơ hội bán hàng B2B - Minh An Company
    Thực thi quy trình 10 bước khép kín phối hợp giữa 4 Skills nghiệp vụ và 2 Human Checkpoints.
    """
    def __init__(self):
        self.catalog = OFFICIAL_CATALOG
        self.sales_reps = SALES_REPRESENTATIVES
        self.policy = DISCOUNT_APPROVAL_POLICY
        self.audit_logs = []
        self.opportunities = []
        
        # Pre-build sorted aliases for exact matching
        self._all_aliases = []
        for sku, pdata in self.catalog.items():
            for alias in pdata['aliases']:
                self._all_aliases.append((len(alias), alias.lower(), sku, pdata))
        self._all_aliases.sort(key=lambda x: x[0], reverse=True)
        
        # Khởi tạo mặc định ở trạng thái DỮ LIỆU TRỐNG (Zero-state)
        # self._init_default_opportunities()

    def reset_to_empty(self):
        """Làm sạch toàn bộ cơ hội bán hàng và nhật ký audit về trạng thái trống ban đầu."""
        self.opportunities = []
        self.audit_logs = []
        return True

    def seed_demo_opportunities(self):
        """Nạp lại 4 test case mẫu khi cần trình diễn/demo."""
        self.reset_to_empty()
        self._init_default_opportunities()
        return len(self.opportunities)

    def _log_audit(self, opp_id, step_name, agent_skill, action, input_data, output_data, rule_applied=None, human_intervention=False):
        log_entry = {
            "id": f"LOG-{len(self.audit_logs)+1:04d}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "opp_id": opp_id,
            "step": step_name,
            "skill": agent_skill,
            "action": action,
            "rule": rule_applied or "Theo quy chuẩn quy trình TO-BE",
            "input_preview": str(input_data)[:220],
            "output_preview": str(output_data)[:220],
            "human_checkpoint": human_intervention
        }
        self.audit_logs.insert(0, log_entry)
        return log_entry

    def match_sku_specific(self, text):
        text_low = text.lower()
        for _, alias, sku, pdata in self._all_aliases:
            if alias in text_low:
                return sku, pdata
        return None, None

    # ==========================================
    # SKILL 1: CUSTOMER REQUEST ANALYZER
    # ==========================================
    def skill1_analyze_request(self, raw_text, source="Email / Web Form"):
        extracted = {
            "customer_name": None,
            "contact_person": None,
            "email": None,
            "phone": None,
            "budget": None,
            "deadline_days": None,
            "requested_discount": 0.0,
            "products_requested": [],
            "approver_info": None,
            "raw_text": raw_text
        }

        # 1. Trích xuất tên công ty / khách hàng
        cust_matches = re.findall(r"(?:Công ty|Tập đoàn|Doanh nghiệp|Khách sạn|Đơn vị|Trường|Bệnh viện|Nhà máy|Trung tâm)\s+([A-ZÀ-Ỹa-zà-ỹ0-9\s\.\&]+?)(?=\s*\(|\s*\n|\s*,|\s*\||\s*cần|\s*-|\s*:|$)", raw_text, re.IGNORECASE)
        valid_cust = None
        for cm in cust_matches:
            clean_cm = cm.strip()
            if not re.search(r"^(Nhà cung cấp|Bên bán|Đơn vị cung ứng|Minh An)$", clean_cm, re.I) and len(clean_cm) > 2:
                valid_cust = clean_cm
                break
        if valid_cust:
            extracted["customer_name"] = valid_cust
        else:
            non_banner_lines = [l.strip() for l in raw_text.strip().split("\n") if l.strip() and not l.strip().startswith("[TẬP TIN")]
            first_line = non_banner_lines[0] if non_banner_lines else ""
            extracted["customer_name"] = first_line[:50].strip() if len(first_line) > 5 else "Doanh nghiệp B2B (Chờ xác nhận)"

        # 2. Email & Phone
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
        if email_match:
            extracted["email"] = email_match.group(0)

        phone_match = re.search(r"(?:^|[\s\(:\|])((?:0|\+84)[0-9\s\.\-]{8,12})(?=$|[\s\),\|])", raw_text)
        if phone_match and not re.match(r"^0\d{2}-\d{2}-\d{2}$", phone_match.group(1).strip()):
            extracted["phone"] = phone_match.group(1).strip()

        # 3. Người liên hệ
        contact_match = re.search(r"(?:Người liên hệ|Đại diện|Liên hệ|Tôi là|Anh|Chị|Ông|Bà)\s*[:\s]\s*([A-ZÀ-Ỹ][A-Za-zÀ-ỹ\s]+?)(?=\s*[\(,\n\r\-]|\s*Trưởng|\s*Phòng|\s*Email|\s*SĐT|$)", raw_text, re.IGNORECASE)
        if contact_match:
            extracted["contact_person"] = contact_match.group(1).strip()
        else:
            extracted["contact_person"] = "Đại diện Mua sắm B2B"

        # 4. Ngân sách
        # Kiểm tra nếu khách ghi rõ chưa xác định ngân sách
        if re.search(r"(?:chưa xác định|không đề cập|phụ thuộc|chưa rõ|chưa có)\s*(?:ngân sách|budget)?", raw_text, re.IGNORECASE) and not re.search(r"\d+\s*(?:triệu|tỷ)", raw_text):
            extracted["budget"] = None
        else:
            budget_match = re.search(r"(?:ngân sách|budget|chi phí|tài chính|hạn mức)[^\d\n\r]{0,35}?(\d+(?:[\.,]\d+)?)\s*(triệu|tr|tỷ|vnđ|vnd|đ)", raw_text, re.IGNORECASE)
            if budget_match:
                num = float(budget_match.group(1).replace(".", "").replace(",", "."))
                unit = budget_match.group(2).lower()
                if "tỷ" in unit:
                    extracted["budget"] = num * 1000000000
                else:
                    extracted["budget"] = num * 1000000
            else:
                extracted["budget"] = None

        # 5. Thời hạn triển khai (ngày)
        if re.search(r"(?:chưa có ngày|chưa rõ ngày|chưa xác định ngày|càng sớm càng tốt)", raw_text, re.IGNORECASE) and not re.search(r"(?:trong|vòng)\s*\d+\s*ngày", raw_text):
            extracted["deadline_days"] = None
        else:
            deadline_match = re.search(r"(?:thời hạn|tiến độ|triển khai|giao trong|vòng)[^\d\n\r]{0,25}?(\d+)\s*(ngày|tuần|tháng)", raw_text, re.IGNORECASE)
            if deadline_match:
                num_days = int(deadline_match.group(1))
                unit = deadline_match.group(2).lower()
                if "tuần" in unit:
                    num_days *= 7
                elif "tháng" in unit:
                    num_days *= 30
                extracted["deadline_days"] = num_days
            else:
                extracted["deadline_days"] = None

        # 6. Yêu cầu chiết khấu
        discount_match = re.search(r"(?:chiết khấu|discount|giảm giá)[^\d\n\r%]{0,25}?(\d+(?:[\.,]\d+)?)\s*%", raw_text, re.IGNORECASE)
        if discount_match:
            extracted["requested_discount"] = float(discount_match.group(1).replace(",", "."))
        else:
            extracted["requested_discount"] = 0.0

        # 7. Người phê duyệt
        approver_match = re.search(r"(?:người phê duyệt|người ký duyệt|approver|giám đốc ký)\s*:\s*([^\n,\r]+)", raw_text, re.IGNORECASE)
        if approver_match:
            extracted["approver_info"] = approver_match.group(1).strip()

        # 8. Trích xuất danh sách sản phẩm & số lượng
        lines = raw_text.split("\n")
        rfq_tabular_map = {
            "switch 24 port": "SW-24P-01",
            "sw-24p-01": "SW-24P-01",
            "switch 48 port": "SW-48P-01",
            "sw-48p-01": "SW-48P-01",
            "router": "RT-EDGE-01",
            "router edge 1g": "RT-EDGE-01",
            "rt-edge-01": "RT-EDGE-01",
            "access point wi-fi 6": "AP-W6-01",
            "access point wifi 6": "AP-W6-01",
            "ap-w6-01": "AP-W6-01",
            "firewall": "FW-EDGE-01",
            "firewall edge": "FW-EDGE-01",
            "fw-edge-01": "FW-EDGE-01"
        }
        primary_rfq_id = None
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Hỗ trợ định dạng bảng RFQ (RFQ-001 | Công ty An Phát | Switch 24 port | 11 | Hà Nội | 2026-03-19 | ...)
            if "|" in line_str:
                parts = [p.strip() for p in line_str.split("|")]
                if len(parts) >= 4 and re.match(r"^RFQ-\d+$", parts[0], re.IGNORECASE):
                    curr_rfq = parts[0].upper()
                    if primary_rfq_id is None:
                        primary_rfq_id = curr_rfq
                        if len(parts[1]) > 2 and not re.match(r"^[A-Z]{2,3}-", parts[1]):
                            extracted["customer_name"] = parts[1]
                    if curr_rfq == primary_rfq_id:
                        # Trong RFQ_Requirements: parts[2]=Item_Name, parts[3]=Quantity
                        # Trong Quotation_Data: parts[1]=Product_ID, parts[2]=Quantity
                        item_candidate = parts[2].lower()
                        qty_candidate = parts[3]
                        if item_candidate not in rfq_tabular_map and parts[1].lower() in rfq_tabular_map:
                            item_candidate = parts[1].lower()
                            qty_candidate = parts[2]
                        mapped_sku = rfq_tabular_map.get(item_candidate)
                        if mapped_sku and mapped_sku in self.catalog:
                            pdata = self.catalog[mapped_sku]
                            qty_val = int(qty_candidate) if qty_candidate.isdigit() else 1
                            existing = [x for x in extracted["products_requested"] if x["sku"] == mapped_sku]
                            if not existing:
                                extracted["products_requested"].append({
                                    "sku": mapped_sku,
                                    "name": pdata["name"],
                                    "quantity": qty_val,
                                    "unit_price": pdata["unit_price"]
                                })
                        if extracted["deadline_days"] is None:
                            extracted["deadline_days"] = 14
                        if extracted["budget"] is None:
                            extracted["budget"] = 500000000
                        if extracted["requested_discount"] == 0.0:
                            extracted["requested_discount"] = 8.0
                    continue

            # Kiểm tra dòng có chứa bullet hoặc có vẻ là sản phẩm
            is_bullet = line_str.startswith(("-", "*", "+", "•"))
            sku, pdata = self.match_sku_specific(line_str)
            
            if sku:
                # Tìm số lượng đi kèm trong dòng
                clean_line = line_str.strip("-*+• \t")
                # 1. Tìm theo từ khóa: số lượng / sl / qty / x: 10
                qty_match = re.search(r"(?:số lượng|sl|qty|x)\s*[:\s]?\s*(\d+)", clean_line, re.IGNORECASE)
                # 2. Tìm theo cấu trúc hai chấm kèm số: Tên sản phẩm: 02 bộ, : 4 cái, : 10
                if not qty_match:
                    qty_match = re.search(r":\s*(\d+)\s*(?:chiếc|bộ|cái|máy|thiết bị|chiếc máy|đơn vị)?(?:\s|$)", clean_line, re.IGNORECASE)
                # 3. Tìm số đứng trước tên sản phẩm: 10 chiếc laptop...
                if not qty_match:
                    qty_match = re.search(r"(?:^|[\s:])(\d+)\s*(?:chiếc|bộ|cái|chiếc máy|thiết bị|máy|đơn vị)?\s+(?:laptop|màn|máy|thiết bị|server|switch|router|camera|hp|dell|cisco|lenovo)", clean_line, re.IGNORECASE)
                # 4. Tìm số ở đầu dòng: 10 laptop...
                if not qty_match:
                    qty_match = re.match(r"^(?:\d+[\.\)]\s*)?(\d+)\s*(?:chiếc|bộ|cái|thiết bị|máy)?\s+", clean_line, re.IGNORECASE)
                # 5. Bất kỳ số kèm đơn vị tính trên dòng: 2 bộ, 4 cái, 10 chiếc
                if not qty_match:
                    qty_match = re.search(r"\b(\d+)\s*(?:chiếc|bộ|cái|máy|thiết bị|chiếc máy|đơn vị)\b", clean_line, re.IGNORECASE)

                if qty_match:
                    qty = int(qty_match.group(1))
                else:
                    # Nếu có ghi rõ "chưa rõ số lượng" hoặc không có số lượng
                    qty = None

                # Tránh trùng SKU trong cùng 1 request
                existing = [x for x in extracted["products_requested"] if x["sku"] == sku]
                if not existing:
                    extracted["products_requested"].append({
                        "sku": sku,
                        "name": pdata["name"],
                        "quantity": qty,
                        "unit_price": pdata["unit_price"]
                    })

        return extracted

    # ==========================================
    # SKILL 2: PRODUCT & INVENTORY VALIDATOR
    # ==========================================
    def skill2_validate_inventory(self, products_requested, deadline_days):
        items_result = []
        is_all_catalog_valid = True
        is_all_stock_sufficient = True
        is_lead_time_feasible = True
        unmet_reasons = []

        if not products_requested:
            is_all_catalog_valid = False
            unmet_reasons.append("Chưa xác định được sản phẩm yêu cầu hợp lệ.")

        for p in products_requested:
            sku = p.get("sku")
            qty = p.get("quantity")

            if sku not in self.catalog:
                is_all_catalog_valid = False
                unmet_reasons.append(f"Sản phẩm '{p.get('name')}' không thuộc danh mục phân phối chính thức của hệ thống.")
                items_result.append({
                    "sku": "CHƯA_XÁC_ĐỊNH",
                    "name": p.get("name"),
                    "requested_qty": qty or 0,
                    "unit_price": 0,
                    "stock_available": 0,
                    "stock_status": "Không có trong danh mục",
                    "standard_lead_days": None,
                    "is_valid": False
                })
                continue

            official = self.catalog[sku]
            stock = official["stock_available"]
            std_lead = official["standard_lead_days"]
            exp_lead = official["express_lead_days"]
            price = official["unit_price"]

            if qty is None:
                # Chưa rõ số lượng
                items_result.append({
                    "sku": sku,
                    "name": official["name"],
                    "requested_qty": 0,
                    "unit_price": price,
                    "stock_available": stock,
                    "stock_status": f"Chưa rõ số lượng (Kho còn {stock})",
                    "standard_lead_days": std_lead,
                    "express_lead_days": exp_lead,
                    "is_stock_ok": False,
                    "is_lead_ok": True,
                    "is_valid": True
                })
                continue

            stock_ok = stock >= qty
            if not stock_ok:
                is_all_stock_sufficient = False
                unmet_reasons.append(f"Tồn kho SKU {sku} hiện chỉ còn {stock} chiếc, không đủ đáp ứng số lượng {qty} yêu cầu.")

            lead_ok = True
            if deadline_days is not None:
                if stock_ok:
                    if std_lead > deadline_days:
                        lead_ok = False
                        is_lead_time_feasible = False
                        unmet_reasons.append(f"Thời gian giao hàng chuẩn ({std_lead} ngày) vượt quá hạn chót của khách ({deadline_days} ngày).")
                else:
                    restock_lead = std_lead + 10
                    if restock_lead > deadline_days:
                        lead_ok = False
                        is_lead_time_feasible = False
                        unmet_reasons.append(f"Hàng không đủ tồn ({stock}/{qty}), thời gian nhập bổ sung ({restock_lead} ngày) không kịp hạn ({deadline_days} ngày).")

            items_result.append({
                "sku": sku,
                "name": official["name"],
                "requested_qty": qty,
                "unit_price": price,
                "stock_available": stock,
                "stock_status": "Đủ tồn kho" if stock_ok else f"Thiếu ({stock}/{qty})",
                "standard_lead_days": std_lead,
                "express_lead_days": exp_lead,
                "is_stock_ok": stock_ok,
                "is_lead_ok": lead_ok,
                "is_valid": True
            })

        return {
            "items": items_result,
            "is_all_catalog_valid": is_all_catalog_valid,
            "is_all_stock_sufficient": is_all_stock_sufficient,
            "is_lead_time_feasible": is_lead_time_feasible,
            "unmet_reasons": unmet_reasons
        }

    # ==========================================
    # SKILL 3: PRICING & DISCOUNT CALCULATOR
    # ==========================================
    def skill3_calculate_pricing(self, validated_items, requested_discount, customer_budget):
        total_before_discount = 0
        has_invalid_item = False

        for item in validated_items:
            qty = item.get("requested_qty") or 0
            price = item.get("unit_price") or 0
            total_before_discount += price * qty

        discount_pct = requested_discount if requested_discount is not None else 0.0
        discount_amount = int(total_before_discount * (discount_pct / 100.0))
        total_after_discount = total_before_discount - discount_amount

        requires_manager_approval = False
        requires_director_approval = False
        approval_reasons = []

        # Kiểm tra ngưỡng chiết khấu theo chính sách
        if discount_pct > self.policy["sales_manager_max_discount"]:
            requires_director_approval = True
            approval_reasons.append(f"Chiết khấu yêu cầu {discount_pct}% vượt hạn mức Trưởng phòng (15%), cần Ban Giám Đốc phê duyệt.")
        elif discount_pct > self.policy["sales_rep_max_discount"]:
            requires_manager_approval = True
            approval_reasons.append(f"Chiết khấu yêu cầu {discount_pct}% vượt hạn mức thẩm quyền của Nhân viên kinh doanh (tối đa 5.0%), cần Trưởng phòng Kinh doanh phê duyệt.")

        # Kiểm tra ngưỡng giá trị hợp đồng lớn
        if total_after_discount >= self.policy["high_value_contract_threshold"]:
            requires_manager_approval = True
            approval_reasons.append(f"Tổng giá trị đơn hàng ({total_after_discount:,.0f} VNĐ) đạt hoặc vượt ngưỡng hợp đồng lớn (500,000,000 VNĐ).")

        # So sánh ngân sách
        is_budget_exceeded = False
        budget_diff = 0
        if customer_budget is not None and customer_budget > 0 and total_after_discount > 0:
            if total_after_discount > customer_budget:
                is_budget_exceeded = True
                budget_diff = total_after_discount - customer_budget

        approval_reason = " | ".join(approval_reasons) if approval_reasons else None

        return {
            "total_before_discount": total_before_discount,
            "discount_percentage": discount_pct,
            "discount_amount": discount_amount,
            "total_after_discount": total_after_discount,
            "customer_budget": customer_budget,
            "is_budget_exceeded": is_budget_exceeded,
            "budget_diff": budget_diff,
            "requires_manager_approval": requires_manager_approval,
            "requires_director_approval": requires_director_approval,
            "approval_reason": approval_reason,
            "math_formula": f"Tổng = ∑(Số lượng × Đơn giá niêm yết) = {total_before_discount:,.0f} đ; Chiết khấu {discount_pct}% = -{discount_amount:,.0f} đ; Tổng thanh toán = {total_after_discount:,.0f} đ"
        }

    # ==========================================
    # SKILL 4: OPPORTUNITY & RESPONSE GENERATOR
    # ==========================================
    def skill4_generate_opportunity_artifacts(self, extracted, validation, pricing, sales_rep):
        missing_fields = []
        if not extracted.get("customer_name") or "Chờ xác nhận" in extracted.get("customer_name"):
            missing_fields.append("Tên công ty / Tổ chức")
        if not extracted.get("products_requested"):
            missing_fields.append("Danh sách sản phẩm")
        else:
            for p in extracted.get("products_requested"):
                if p.get("quantity") is None or p.get("quantity") <= 0:
                    missing_fields.append(f"Số lượng cho sản phẩm {p.get('name')}")
        if extracted.get("budget") is None:
            missing_fields.append("Ngân sách dự kiến của dự án")
        if extracted.get("deadline_days") is None:
            missing_fields.append("Thời hạn / Tiến độ cần bàn giao thiết bị")

        is_info_complete = len(missing_fields) == 0

        # Điểm Quyết định 2: Phân loại cơ hội thành 4 trạng thái
        status = ""
        status_reason = ""
        next_step = ""

        if not is_info_complete:
            status = "Cần bổ sung thông tin"
            status_reason = f"Yêu cầu còn thiếu các thông tin bắt buộc: {', '.join(missing_fields)}."
            next_step = f"Chuyên viên {sales_rep['name']} gửi email làm rõ tới khách hàng theo bảng câu hỏi đã soạn sẵn."
        elif not validation["is_all_catalog_valid"] or not validation["is_all_stock_sufficient"] or not validation["is_lead_time_feasible"]:
            status = "Chưa đáp ứng"
            status_reason = "; ".join(validation["unmet_reasons"])
            next_step = "Liên hệ khách hàng để tư vấn đổi cấu hình tương đương hoặc đàm phán kéo dài tiến độ bàn giao."
        elif pricing["is_budget_exceeded"]:
            status = "Chưa đáp ứng"
            status_reason = f"Tổng chi phí sau chiết khấu ({pricing['total_after_discount']:,.0f} đ) vượt quá ngân sách khách hàng ({pricing['customer_budget']:,.0f} đ) {pricing['budget_diff']:,.0f} đ."
            next_step = "Đề xuất khách hàng cân đối số lượng hoặc bổ sung hạn mức ngân sách."
        elif pricing["requires_manager_approval"] or pricing["requires_director_approval"]:
            status = "Chờ duyệt"
            status_reason = pricing["approval_reason"]
            next_step = f"AI Agent lập Phiếu chuyển duyệt trình Trưởng phòng Kinh doanh ({self.policy['manager_name']}) xem xét."
        else:
            status = "Có thể tiếp tục"
            status_reason = "Yêu cầu đầy đủ thông tin, sản phẩm trong danh mục, tồn kho đủ, thời hạn khả thi và chiết khấu trong thẩm quyền Sales."
            next_step = f"Chuyên viên {sales_rep['name']} hoàn thiện hồ sơ báo giá chính thức và gửi khách hàng."

        draft_email = self._compose_draft_email(extracted, validation, pricing, status, missing_fields, sales_rep)
        approval_ticket = None
        if status == "Chờ duyệt":
            approval_ticket = self._compose_approval_ticket(extracted, validation, pricing, sales_rep)

        return {
            "status": status,
            "status_reason": status_reason,
            "missing_fields": missing_fields,
            "next_step": next_step,
            "draft_email": draft_email,
            "approval_ticket": approval_ticket
        }

    def _compose_draft_email(self, extracted, validation, pricing, status, missing_fields, sales_rep):
        extracted = extracted or {}
        validation = validation or {}
        pricing = pricing or {}
        sales_rep = sales_rep or {"name": "Lê Yến Như", "role": "Chuyên viên Quản trị BI", "email": "contact@minhan.com.vn"}

        customer = extracted.get("customer_name") or "Quý khách"
        contact = extracted.get("contact_person") or "Quý khách"

        if status == "Cần bổ sung thông tin":
            missing_fields = missing_fields or []
            questions = "\n".join([f"  {idx+1}. Quý khách vui lòng cung cấp thêm: {item}" for idx, item in enumerate(missing_fields)])
            return f"""Kính gửi Anh/Chị {contact} - {customer},

Bộ phận Kinh doanh B2B xin trân trọng cảm ơn Quý khách đã quan tâm và gửi yêu cầu hợp tác mua sắm thiết bị.

Để bộ phận kỹ thuật và kinh doanh lập bảng báo giá chính xác và tối ưu nhất cho Quý công ty, chúng tôi kính đề nghị Quý khách hỗ trợ làm rõ một số nội dung sau:

{questions}

Ngay khi nhận được thông tin bổ sung, chuyên viên phụ trách sẽ lập tức hoàn thiện hồ sơ và gửi báo giá chính thức trong vòng 04 giờ làm việc.

Kính chúc Quý công ty ngày làm việc hiệu quả và thành công!

Trân trọng,
---------------------------------------
{sales_rep.get('name', 'Chuyên viên')} | {sales_rep.get('role', 'Bộ phận Kinh doanh')}
Bộ Phận Bán Hàng Doanh Nghiệp B2B
Hotline: 1900 6868 | Email: {sales_rep.get('email', 'contact@minhan.com.vn')}"""

        elif status == "Có thể tiếp tục":
            val_items = validation.get("items", []) or []
            if val_items:
                items_str = "\n".join([f"  • {it.get('name', 'Sản phẩm')}: {it.get('requested_qty', 1)} chiếc × {it.get('unit_price', 0):,.0f} VNĐ" for it in val_items])
                lead_days = val_items[0].get('standard_lead_days', 3) if isinstance(val_items[0], dict) else 3
            else:
                items_str = "  • Thiết bị & giải pháp công nghệ theo hồ sơ yêu cầu"
                lead_days = 3

            total_before = pricing.get('total_before_discount', 0)
            disc_pct = pricing.get('discount_percentage', 0)
            disc_amt = pricing.get('discount_amount', 0)
            total_after = pricing.get('total_after_discount', total_before - disc_amt)

            return f"""Kính gửi Anh/Chị {contact} - {customer},

Hệ thống B2B xin chân thành cảm ơn Quý khách đã tin tưởng lựa chọn giải pháp thiết bị của chúng tôi.

Chúng tôi đã thẩm định tồn kho và xác nhận đáp ứng hoàn hảo yêu cầu đơn hàng của Quý công ty:
{items_str}

- Tổng giá trị niêm yết: {total_before:,.0f} VNĐ
- Chiết khấu ưu đãi ({disc_pct}%): -{disc_amt:,.0f} VNĐ
- TỔNG GIÁ TRỊ THANH TOÁN (Chưa VAT): {total_after:,.0f} VNĐ
- Tiến độ giao hàng cam kết: {lead_days} ngày làm việc kể từ khi ký kết hợp đồng.

Bảng báo giá chi tiết và cam kết bảo hành chính hãng đã được đính kèm. Kính mong sớm nhận được phản hồi từ Quý công ty!

Trân trọng,
---------------------------------------
{sales_rep.get('name', 'Chuyên viên')} | {sales_rep.get('role', 'Bộ phận Kinh doanh')}
Bộ Phận Bán Hàng Doanh Nghiệp B2B | Email: {sales_rep.get('email', 'contact@minhan.com.vn')}"""

        elif status == "Chờ duyệt":
            disc_pct = pricing.get('discount_percentage', 0)
            return f"""Kính gửi Anh/Chị {contact} - {customer},

Hệ thống B2B đã tiếp nhận đầy đủ thông tin đơn hàng và đề xuất mức chiết khấu {disc_pct}% của Quý công ty.

Do mức chiết khấu này vượt hạn mức ủy quyền tiêu chuẩn của chuyên viên bán hàng, chúng tôi đang lập Phiếu chuyển duyệt đặc biệt trình Trưởng phòng Kinh doanh để phê duyệt mức ưu đãi cao nhất cho dự án của Quý công ty.

Kết quả phê duyệt sẽ được gửi tới Quý khách trước 16h30 hôm nay. Rất mong Quý khách thông cảm cho sự chậm trễ này!

Trân trọng,
---------------------------------------
{sales_rep.get('name', 'Chuyên viên')} | {sales_rep.get('role', 'Bộ phận Kinh doanh')}
Bộ Phận Bán Hàng Doanh Nghiệp B2B"""

        else: # Chưa đáp ứng
            reasons_list = validation.get("unmet_reasons", []) or []
            if not reasons_list:
                reasons_list = ["Tồn kho khả dụng hiện tại chưa đủ số lượng yêu cầu hoặc sản phẩm cần thời gian nhập khẩu bổ sung."]
            reasons = "\n".join([f"  • {r}" for r in reasons_list])
            return f"""Kính gửi Anh/Chị {contact} - {customer},

Bộ phận Kinh doanh B2B xin trân trọng cảm ơn Quý khách đã gửi yêu cầu đặt hàng thiết bị.

Sau khi đối chiếu năng lực cung ứng thực tế tại hệ thống kho vận, chúng tôi rất tiếc phải thông báo hiện tại đơn hàng chưa thể đáp ứng ngay vì các lý do sau:
{reasons}

Phương án đề xuất tối ưu:
1. Giao trước số lượng hàng hiện có trong kho, số còn lại sẽ giao ngay khi đợt nhập khẩu bổ sung hoàn tất.
2. Hoặc tư vấn cấu hình sản phẩm tương đương đang sẵn sàng tại kho với hiệu năng tương tự.

Chuyên viên phụ trách sẽ gọi điện trực tiếp để tư vấn và thống nhất phương án thuận tiện nhất cho Quý khách.

Trân trọng,
---------------------------------------
{sales_rep.get('name', 'Chuyên viên')} | {sales_rep.get('role', 'Bộ phận Kinh doanh')}
Bộ Phận Bán Hàng Doanh Nghiệp B2B"""

    def _compose_approval_ticket(self, extracted, validation, pricing, sales_rep):
        extracted = extracted or {}
        validation = validation or {}
        pricing = pricing or {}
        sales_rep = sales_rep or {"name": "Lê Yến Như", "role": "Chuyên viên Quản trị BI", "email": "contact@minhan.com.vn"}

        val_items = validation.get('items', []) or []
        if val_items:
            items_str = "\n".join([f"• {it.get('name', 'Sản phẩm')}: {it.get('requested_qty', 1)} chiếc (Đơn giá: {it.get('unit_price', 0):,.0f} đ, Tồn kho: {it.get('stock_available', 0)})" for it in val_items])
        else:
            items_str = "• Thiết bị & giải pháp công nghệ theo đề xuất"

        disc_pct = pricing.get("discount_percentage", 0)
        total_after = pricing.get("total_after_discount", 0)
        return {
            "ticket_id": f"APV-{datetime.datetime.now().strftime('%Y%m%d')}-{len(self.opportunities)+1:03d}",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "customer_name": extracted.get("customer_name") or "Khách hàng B2B",
            "sales_rep": sales_rep.get("name", "Chuyên viên"),
            "approver_target": self.policy.get("manager_name", "Trưởng phòng Kinh doanh"),
            "approver_title": self.policy.get("manager_title", "Trưởng phòng Kinh doanh"),
            "items_summary": items_str,
            "total_before_discount": pricing.get("total_before_discount", 0),
            "requested_discount_pct": disc_pct,
            "discount_amount": pricing.get("discount_amount", 0),
            "total_after_discount": total_after,
            "exceeded_reason": pricing.get("approval_reason", "Chiết khấu vượt hạn mức 5%"),
            "data_evidence": f"Chính sách quy định Sales Rep tối đa 5.0%. Mức đề xuất {disc_pct}% vượt hạn mức {max(0, disc_pct - 5.0):.1f}%. Tổng giá trị hợp đồng: {total_after:,.0f} VNĐ.",
            "recommendation": "Kiến nghị Trưởng phòng phê duyệt nhằm giữ chân khách hàng doanh nghiệp chiến lược và đạt chỉ tiêu doanh số quý.",
            "status": "CHỜ DUYỆT"
        }

    # ==========================================
    # QUY TRÌNH 10 BƯỚC THỐNG NHẤT (END-TO-END)
    # ==========================================
    def process_b2b_opportunity(self, raw_text, source="Email / Web Form", assigned_sales_index=None, context=None):
        opp_id = f"OPP-2026-{len(self.opportunities)+1:03d}"

        # Bước 1: Tiếp nhận yêu cầu
        self._log_audit(opp_id, "Bước 1: Tiếp nhận yêu cầu", "Request Ingestion", "Ghi nhận nội dung và nguồn dữ liệu", raw_text, f"Tạo ID: {opp_id}, Nguồn: {source}")

        # Bước 2: Phân loại & Trích xuất thông tin (Skill 1)
        extracted = self.skill1_analyze_request(raw_text, source)
        self._log_audit(opp_id, "Bước 2: Phân loại & Trích xuất", "Skill 1: Request Analyzer", "Trích xuất thực thể B2B", raw_text, extracted)

        # Bước 3: Điểm quyết định 1 - Kiểm tra tính đầy đủ
        temp_missing = []
        if not extracted.get("customer_name") or "Chờ xác nhận" in extracted.get("customer_name"):
            temp_missing.append("Tên khách hàng")
        if not extracted.get("products_requested"):
            temp_missing.append("Sản phẩm")
        else:
            for p in extracted.get("products_requested"):
                if p.get("quantity") is None or p.get("quantity") <= 0:
                    temp_missing.append(f"Số lượng cho {p.get('name')}")
        if extracted.get("budget") is None:
            temp_missing.append("Ngân sách")
        if extracted.get("deadline_days") is None:
            temp_missing.append("Thời hạn")

        self._log_audit(opp_id, "Bước 3: Điểm quyết định 1", "Information Validation", "Đánh giá tính đầy đủ dữ liệu", extracted, f"Thiếu: {temp_missing if temp_missing else 'Đầy đủ 100%'}")

        # Bước 4: Tạo hồ sơ cơ hội & Gán người phụ trách
        if assigned_sales_index is None:
            sales_rep = self.sales_reps[len(self.opportunities) % len(self.sales_reps)]
        else:
            sales_rep = self.sales_reps[assigned_sales_index % len(self.sales_reps)]
        self._log_audit(opp_id, "Bước 4: Tạo hồ sơ & Gán Sales", "Opportunity Management", "Gán nhân viên kinh doanh phụ trách", f"Sales ID: {sales_rep['id']}", sales_rep)

        # Bước 5: Thẩm định danh mục, tồn kho và giá (Skill 2)
        validation = self.skill2_validate_inventory(extracted["products_requested"], extracted.get("deadline_days"))
        self._log_audit(opp_id, "Bước 5: Thẩm định Tồn kho & Giá", "Skill 2: Inventory Validator", "Đối chiếu Master Catalog & Lead-time", extracted["products_requested"], validation)

        # Bước 6: Tính giá và lập đề xuất (Skill 3)
        pricing = self.skill3_calculate_pricing(validation["items"], extracted.get("requested_discount"), extracted.get("budget"))
        self._log_audit(opp_id, "Bước 6: Tính giá & Chiết khấu", "Skill 3: Pricing Calculator", "Áp dụng chính sách & Ngưỡng phê duyệt", validation["items"], pricing)

        # Bước 7 & Bước 9: Quyết định 2 & Hoàn thiện hồ sơ (Skill 4)
        artifacts = self.skill4_generate_opportunity_artifacts(extracted, validation, pricing, sales_rep)
        self._log_audit(opp_id, "Bước 7: Điểm quyết định 2", "Skill 4: Opportunity Generator", "Phân loại trạng thái cơ hội", pricing, f"Status: {artifacts['status']} | Lý do: {artifacts['status_reason']}")

        # Bước 8: Trưởng phòng Kinh doanh phê duyệt (Human Checkpoint 2) nếu cần
        if artifacts["status"] == "Chờ duyệt":
            self._log_audit(opp_id, "Bước 8: Trình duyệt Trưởng phòng", "Human Checkpoint 2", "Tạo Phiếu chuyển duyệt chờ Trưởng phòng ký", artifacts["approval_ticket"], "Chờ con người ra quyết định", human_intervention=True)

        # Bước 10: Kết thúc & Bàn giao quản lý
        full_record = {
            "id": opp_id,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "context": context or {},
            "customer_name": extracted["customer_name"],
            "contact_person": extracted["contact_person"],
            "email": extracted.get("email") or "contact@" + extracted["customer_name"].lower().replace(" ", "")[:10] + ".vn",
            "phone": extracted.get("phone") or "090" + str(len(self.opportunities)*111111)[:7],
            "sales_rep": sales_rep,
            "extracted": extracted,
            "validation": validation,
            "pricing": pricing,
            "status": artifacts["status"],
            "status_reason": artifacts["status_reason"],
            "missing_fields": artifacts["missing_fields"],
            "next_step": artifacts["next_step"],
            "draft_email": artifacts["draft_email"],
            "approval_ticket": artifacts["approval_ticket"],
            "human_decision": None
        }

        self.opportunities.append(full_record)
        self._log_audit(opp_id, "Bước 10: Kết thúc & Bàn giao", "Opportunity Management", "Lưu hồ sơ và đồng bộ Dashboard", full_record["id"], f"Trạng thái cuối: {full_record['status']}")

        return full_record

    def manager_decide_approval(self, opp_id, decision, manager_note=""):
        """
        Human Checkpoint 2: Trưởng phòng Kinh doanh phê duyệt hoặc từ chối phiếu duyệt.
        """
        for opp in self.opportunities:
            if opp["id"] == opp_id:
                opp["human_decision"] = decision
                discount_pct = opp.get("pricing", {}).get("discount_percentage", 0)
                sales_name = opp.get("sales_rep", {}).get("name", "Chuyên viên")
                
                if decision == "APPROVED":
                    opp["status"] = "Có thể tiếp tục"
                    manager_name = self.policy.get("manager_name", "Trưởng phòng Kinh doanh")
                    opp["status_reason"] = f"Trưởng phòng {manager_name} đã phê duyệt chiết khấu đặc biệt ({discount_pct}%). Ghi chú: {manager_note or 'Đồng ý duyệt theo đề xuất'}"
                    opp["next_step"] = f"Chuyên viên {sales_name} phát hành báo giá chính thức theo mức giá đã phê duyệt."
                    opp["draft_email"] = self._compose_draft_email(opp.get("extracted", {}), opp.get("validation", {}), opp.get("pricing", {}), "Có thể tiếp tục", [], opp.get("sales_rep", {}))
                else:
                    opp["status"] = "Chưa đáp ứng"
                    opp["status_reason"] = f"Trưởng phòng từ chối mức chiết khấu {discount_pct}%. Ghi chú: {manager_note or 'Mức chiết khấu không phù hợp biên lợi nhuận'}"
                    opp["next_step"] = f"Chuyên viên {sales_name} đàm phán lại với khách hàng theo mức chiết khấu chuẩn."

                self._log_audit(
                    opp_id,
                    "Bước 8: Phê duyệt của Trưởng phòng",
                    "Human Checkpoint 2",
                    f"Trưởng phòng ra quyết định: {decision}",
                    {"note": manager_note, "approver": self.policy["manager_name"]},
                    f"Cập nhật trạng thái thành: {opp['status']}",
                    human_intervention=True
                )
                return True
        return False

    def get_dashboard_summary(self):
        total = len(self.opportunities)
        stats = {
            "total_count": total,
            "eligible": {"count": 0, "total_value": 0},
            "missing_info": {"count": 0, "total_value": 0},
            "unfulfilled": {"count": 0, "total_value": 0},
            "pending_approval": {"count": 0, "total_value": 0}
        }

        for opp in self.opportunities:
            st = opp["status"]
            val = opp["pricing"]["total_after_discount"] if opp["pricing"]["total_after_discount"] > 0 else 0

            if st == "Có thể tiếp tục":
                stats["eligible"]["count"] += 1
                stats["eligible"]["total_value"] += val
            elif st == "Cần bổ sung thông tin":
                stats["missing_info"]["count"] += 1
            elif st == "Chưa đáp ứng":
                stats["unfulfilled"]["count"] += 1
            elif st == "Chờ duyệt":
                stats["pending_approval"]["count"] += 1
                stats["pending_approval"]["total_value"] += val

        return stats

    def _init_default_opportunities(self):
        tc1_text = """Kính gửi Bộ phận Kinh doanh & Cung ứng B2B,
Tôi là Trần Văn Hùng, Trưởng phòng CNTT Công ty Cổ phần Công nghệ DigiTech (Email: hung.tran@digitech.vn, SĐT: 0912345678).
Công ty chúng tôi đang cần trang bị thiết bị cho nhân viên mới:
- 10 chiếc Laptop Doanh Nghiệp Dell Vostro 5630
- 5 bộ Màn hình Dell P2422H 23.8 inch IPS Full HD
Ngân sách dự kiến của chúng tôi là 250 triệu VNĐ.
Tiến độ triển khai trong vòng 7 ngày làm việc kể từ khi ký hợp đồng.
Đề xuất mức chiết khấu thân thiết là 4%.
Nhờ quý công ty gửi báo giá và cam kết bảo hành giúp tôi. Xin cảm ơn!"""

        tc2_text = """Gửi Phòng Kinh doanh Doanh nghiệp B2B,
Công ty Tập đoàn Dược Phẩm An Khang cần mua sắm gấp thiết bị:
- Máy chủ Server Dell PowerEdge R450 Rack 1U
- Switch mạng Cisco Catalyst 24 Port Gigabit C1000-24T (chưa rõ số lượng bao nhiêu cái)
Ngân sách: Hiện chưa xác định ngân sách cụ thể, phụ thuộc vào báo giá của nhà cung cấp.
Thời hạn: Cần càng sớm càng tốt nhưng chưa có ngày cụ thể.
Người liên hệ: Nguyễn Thu Trang - Phòng Mua sắm (Email: trang.nt@ankhangpharma.com)."""

        tc3_text = """Kính gửi Bộ phận Bán hàng B2B Doanh nghiệp,
Công ty Cổ phần Viễn Thông Toàn Cầu (Global Telecom JSC) cần đặt mua:
- 30 chiếc Thiết bị định tuyến Router Cisco Catalyst C8200L
Số lượng đặt mua lớn và thanh toán ngay 100%, chúng tôi yêu cầu mức chiết khấu thương mại 10%.
Ngân sách công ty bố trí: 700 triệu VNĐ.
Thời hạn giao hàng: trong vòng 10 ngày.
Người phê duyệt hợp đồng: Ông Lê Minh Quân - Tổng Giám Đốc.
Người liên hệ: Ban Mua Sắm (ban.muasam@globaltelecom.vn - SĐT: 0988776655)."""

        tc4_text = """Gửi Đơn vị Cung ứng Thiết bị B2B,
Công ty Khách sạn Grand Plaza Hà Nội cần đặt mua khẩn cấp:
- 50 chiếc Máy in Laser đa năng HP LaserJet Pro MFP M428fdw
Yêu cầu: Giao hàng toàn bộ và lắp đặt hoàn thiện trong vòng 3 ngày tới để kịp khai trương trung tâm hội nghị.
Ngân sách dự kiến: 600 triệu VNĐ. Chiết khấu mong muốn: 2%.
Người liên hệ: Vũ Đức Thắng - Quản lý Vận hành (Email: thang.vd@grandplazahotel.vn)."""

        self.process_b2b_opportunity(tc1_text, "Email khách hàng (Test Case 1: Tiêu chuẩn)", 0)
        self.process_b2b_opportunity(tc2_text, "Biểu mẫu Web (Test Case 2: Thiếu dữ liệu)", 1)
        self.process_b2b_opportunity(tc3_text, "Email khách hàng (Test Case 3: Vượt quyền 10%)", 2)
        self.process_b2b_opportunity(tc4_text, "Email khách hàng (Test Case 4: Thiếu tồn kho)", 3)

