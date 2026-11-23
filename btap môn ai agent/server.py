import http.server
import socketserver
import json
import os
import urllib.parse
import hashlib
import time
import base64
import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from modules.b2b_agent import B2BOpportunityOrchestrator
from modules.b2b_catalog import OFFICIAL_CATALOG, SALES_REPRESENTATIVES, DISCOUNT_APPROVAL_POLICY

def parse_xlsx_bytes(raw_bytes: bytes, max_rows: int = 200000):
    """Parse .xlsx spreadsheet using Python stdlib (zipfile + ElementTree)."""
    import re
    with zipfile.ZipFile(io.BytesIO(raw_bytes), 'r') as z:
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in root.findall('.//s:si', ns):
                texts = [t.text or '' for t in si.findall('.//s:t', ns)]
                shared_strings.append(''.join(texts))

        sheet_names = [n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
        sheet_names.sort(key=lambda n: int(re.search(r'(\d+)\.xml$', n).group(1)) if re.search(r'(\d+)\.xml$', n) else 0)
        if not sheet_names:
            return {"headers": [], "rows": [], "total_rows": 0}

        sheet_root = ET.fromstring(z.read(sheet_names[0]))
        ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

        def col_to_idx(ref_str):
            letters = ''.join(ch for ch in ref_str if ch.isalpha())
            idx = 0
            for ch in letters:
                idx = idx * 26 + (ord(ch.upper()) - ord('A') + 1)
            return max(0, idx - 1)

        all_rows = []
        for row_el in sheet_root.findall('.//s:sheetData/s:row', ns):
            row_dict = {}
            max_col = -1
            for c in row_el.findall('s:c', ns):
                ref = c.attrib.get('r', '')
                c_idx = col_to_idx(ref) if ref else (max_col + 1)
                if c_idx > max_col:
                    max_col = c_idx
                c_type = c.attrib.get('t', '')
                val = ''
                if c_type == 'inlineStr':
                    texts = [t.text or '' for t in c.findall('.//s:t', ns)]
                    val = ''.join(texts)
                else:
                    v_el = c.find('s:v', ns)
                    raw_v = v_el.text if (v_el is not None and v_el.text is not None) else ''
                    if c_type == 's' and raw_v.isdigit():
                        s_i = int(raw_v)
                        val = shared_strings[s_i] if s_i < len(shared_strings) else raw_v
                    else:
                        val = raw_v
                row_dict[c_idx] = str(val)

            if max_col >= 0:
                row_list = [row_dict.get(i, '') for i in range(max_col + 1)]
                if any(str(cell).strip() != '' for cell in row_list):
                    all_rows.append(row_list)

        if not all_rows:
            return {"headers": [], "rows": [], "total_rows": 0}

        headers = [str(h).strip() for h in all_rows[0]]
        data_rows = all_rows[1:]
        col_count = len(headers)
        normalized_rows = []
        for r in data_rows[:max_rows]:
            if len(r) < col_count:
                r = r + [''] * (col_count - len(r))
            elif len(r) > col_count:
                r = r[:col_count]
            normalized_rows.append(r)

        return {
            "headers": [h if h else f"Cột {i+1}" for i, h in enumerate(headers)],
            "rows": normalized_rows,
            "total_rows": len(data_rows)
        }

PORT = int(os.environ.get("PORT", 8888))
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

orchestrator = B2BOpportunityOrchestrator()
PASSWORD_SALT = "minhan_secret_salt_2026"

def hash_password(password: str) -> str:
    return hashlib.sha256((password.strip() + PASSWORD_SALT).encode('utf-8')).hexdigest()

# 1. Cơ sở dữ liệu người dùng chính thức với Mật khẩu đã được Băm bảo mật (Hashed)
# Hỗ trợ cả mật khẩu đơn giản (admin123, manager123, sales123, user123)
USER_DATABASE = {
    "admin@minhan.com.vn": {
        "id": "USR-001",
        "email": "admin@minhan.com.vn",
        "name": "Lê Yến Như",
        "password_hash": hash_password("admin123"),
        "role_code": "ADMIN",
        "role_name": "Quản trị viên & Kiến trúc sư AI",
        "department": "Ban Quản Trị & Công Nghệ",
        "avatar": "/assets/avatar.png?v=2",
        "permissions": ["all", "manage_data", "view_audit", "settings", "approve_all"]
    },
    "yennhu@minhan.com.vn": {
        "id": "USR-001",
        "email": "yennhu@minhan.com.vn",
        "name": "Lê Yến Như",
        "password_hash": hash_password("admin123"),
        "role_code": "ADMIN",
        "role_name": "Quản trị viên & Kiến trúc sư AI",
        "department": "Ban Quản Trị & Công Nghệ",
        "avatar": "/assets/avatar.png?v=2",
        "permissions": ["all", "manage_data", "view_audit", "settings", "approve_all"]
    },
    "tuan.le@minhan.com.vn": {
        "id": "USR-002",
        "email": "tuan.le@minhan.com.vn",
        "name": "Lê Văn Tuấn",
        "password_hash": hash_password("manager123"),
        "role_code": "SALES_MANAGER",
        "role_name": "Trưởng phòng Kinh doanh B2B",
        "department": "Phòng Kinh Doanh Doanh Nghiệp",
        "avatar": "https://api.dicebear.com/7.x/adventurer/png?seed=TuanLe&backgroundColor=fef3c7",
        "permissions": ["view_all_opps", "approve_discount", "export_reports", "view_pricing"]
    },
    "an.nguyen@minhan.com.vn": {
        "id": "USR-003",
        "email": "an.nguyen@minhan.com.vn",
        "name": "Nguyễn Văn An",
        "password_hash": hash_password("sales123"),
        "role_code": "SALES_REP",
        "role_name": "Chuyên viên Kinh doanh B2B (Sales)",
        "department": "Nhóm Kinh Doanh 01",
        "avatar": "https://api.dicebear.com/7.x/adventurer/png?seed=NguyenAn&backgroundColor=dbeafe",
        "permissions": ["create_opp", "view_assigned_opps", "calculate_price"]
    },
    "sales@minhan.com.vn": {
        "id": "USR-003",
        "email": "sales@minhan.com.vn",
        "name": "Nguyễn Văn An",
        "password_hash": hash_password("sales123"),
        "role_code": "SALES_REP",
        "role_name": "Chuyên viên Kinh doanh B2B (Sales)",
        "department": "Nhóm Kinh Doanh 01",
        "avatar": "https://api.dicebear.com/7.x/adventurer/png?seed=NguyenAn&backgroundColor=dbeafe",
        "permissions": ["create_opp", "view_assigned_opps", "calculate_price"]
    },
    "user@digitech.vn": {
        "id": "USR-004",
        "email": "user@digitech.vn",
        "name": "Trần Văn Hùng",
        "password_hash": hash_password("user123"),
        "role_code": "CUSTOMER",
        "role_name": "Khách hàng Doanh nghiệp (DigiTech)",
        "department": "Công ty Cổ phần DigiTech",
        "avatar": "https://api.dicebear.com/7.x/adventurer/png?seed=HungTran&backgroundColor=e0e7ff",
        "permissions": ["submit_request", "view_own_quotes"]
    }
}

# 2. Bộ nhớ lưu trữ phiên đăng nhập an toàn (Active Sessions + Stateless Signed Token cho Vercel)
ACTIVE_SESSIONS = {}

def _issue_session_token(user_safe_info: dict) -> str:
    """Sinh token vừa lưu trong ACTIVE_SESSIONS vừa ký stateless để sống sót qua serverless cold start."""
    payload_obj = {"user": user_safe_info, "exp": int(time.time()) + 86400}
    raw_b64 = base64.urlsafe_b64encode(json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")).decode("ascii")
    sig = hashlib.sha256((raw_b64 + PASSWORD_SALT).encode("utf-8")).hexdigest()[:24]
    token = f"tok_{raw_b64}.{sig}"
    ACTIVE_SESSIONS[token] = {"user": user_safe_info, "created_at": time.time()}
    return token

def _verify_session_token(token: str):
    if not token:
        return None
    if token in ACTIVE_SESSIONS:
        sess = ACTIVE_SESSIONS[token]
        if time.time() - sess["created_at"] < 86400:
            return sess["user"]
    if token.startswith("tok_") and "." in token:
        try:
            body, sig = token[4:].rsplit(".", 1)
            expected_sig = hashlib.sha256((body + PASSWORD_SALT).encode("utf-8")).hexdigest()[:24]
            if sig == expected_sig:
                payload_obj = json.loads(base64.urlsafe_b64decode(body.encode("ascii")).decode("utf-8"))
                if payload_obj.get("exp", 0) > time.time():
                    return payload_obj.get("user")
        except Exception:
            return None
    return None

class B2BAgentHttpHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def _get_authenticated_user(self):
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        else:
            cookie = self.headers.get("Cookie", "")
            for c in cookie.split(";"):
                if "session_token=" in c:
                    token = c.split("session_token=")[-1].strip()
        
        if token:
            return _verify_session_token(token)
        return None

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/me":
            user = self._get_authenticated_user()
            if user:
                self._send_json({"authenticated": True, "user": user})
            else:
                self._send_error(401, "Chưa đăng nhập hoặc phiên làm việc đã hết hạn!")
            return

        elif path == "/api/summary":
            summary = orchestrator.get_dashboard_summary()
            self._send_json(summary)
            return

        elif path == "/api/opportunities":
            summary = orchestrator.get_dashboard_summary()
            user = self._get_authenticated_user()
            
            # Phân quyền dữ liệu theo vai trò thực tế:
            # - Customer chỉ thấy cơ hội của mình
            # - Sales Rep chỉ thấy cơ hội do mình phụ trách
            # - Manager và Admin thấy toàn bộ
            all_opps = orchestrator.opportunities
            filtered_opps = all_opps
            if user:
                if user["role_code"] == "CUSTOMER":
                    filtered_opps = [o for o in all_opps if "DigiTech" in o["customer_name"] or user["email"] in o.get("email", "")]
                elif user["role_code"] == "SALES_REP":
                    filtered_opps = [o for o in all_opps if o["sales_rep"]["id"] == "SALES-01" or o["sales_rep"]["name"] == user["name"]]

            res = {
                "summary": summary,
                "opportunities": filtered_opps,
                "user_role": user["role_code"] if user else "GUEST"
            }
            self._send_json(res)
            return

        elif path == "/api/catalog":
            res = {
                "catalog": orchestrator.catalog,
                "sales_reps": orchestrator.sales_reps,
                "policy": orchestrator.policy
            }
            self._send_json(res)
            return

        elif path == "/api/audit_logs":
            self._send_json(orchestrator.audit_logs)
            return

        elif path in ["/api/clear_data", "/api/reset_data"]:
            orchestrator.reset_to_empty()
            summary = orchestrator.get_dashboard_summary()
            self._send_json({
                "status": "success",
                "message": "Hệ thống đã được chuyển về trạng thái dữ liệu trống!",
                "summary": summary,
                "opportunities": orchestrator.opportunities
            })
            return

        elif path == "/api/seed_demo_data":
            count = orchestrator.seed_demo_opportunities()
            summary = orchestrator.get_dashboard_summary()
            self._send_json({
                "status": "success",
                "message": f"Đã nạp {count} Test Case mẫu!",
                "summary": summary,
                "opportunities": orchestrator.opportunities
            })
            return

        elif path.startswith("/api/opportunity/"):
            opp_id = path.split("/")[-1]
            found = [o for o in orchestrator.opportunities if o["id"] == opp_id]
            if found:
                self._send_json(found[0])
            else:
                self._send_error(404, "Không tìm thấy cơ hội bán hàng")
            return

        elif path == "/api/export/csv":
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="MinhAn_B2B_Opportunities.csv"')
            self.end_headers()
            
            csv_lines = [
                "\ufeffMã Cơ Hội,Khách Hàng,Người Liên Hệ,Trạng Thái,Tổng Giá Trị (VNĐ),Chiết Khấu (%),Hạn Mức Ngân Sách,Hạn Chót (Ngày),Sales Phụ Trách,Lý Do Nghiệp Vụ"
            ]
            for o in orchestrator.opportunities:
                val = o["pricing"]["total_after_discount"]
                disc = o["pricing"]["discount_percentage"]
                budget = o["extracted"]["budget"] or "Chưa xác định"
                deadline = o["extracted"]["deadline_days"] or "Chưa xác định"
                csv_lines.append(
                    f'"{o["id"]}","{o["customer_name"]}","{o["contact_person"]}","{o["status"]}",{val},{disc},"{budget}","{deadline}","{o["sales_rep"]["name"]}","{o["status_reason"]}"'
                )
            self.wfile.write("\n".join(csv_lines).encode("utf-8"))
            return

        elif path.startswith("/api/export/word"):
            params = urllib.parse.parse_qs(parsed_url.query)
            opp_id = params.get("id", [None])[0]
            target_opps = [o for o in orchestrator.opportunities if o["id"] == opp_id] if opp_id else orchestrator.opportunities
            
            doc_html = self._generate_word_document(target_opps)
            self.send_response(200)
            self.send_header("Content-Type", "application/msword; charset=utf-8")
            fname = f"BaoCao_CoHoi_{opp_id}.doc" if opp_id else "BaoCao_TongHop_CoHoi_MinhAn.doc"
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.end_headers()
            self.wfile.write(doc_html.encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            payload = {}

        # -------------------------------------------------------------
        # PHÂN TÍCH FILE EXCEL (.XLSX) THỰC TẾ SANG BẢNG DỮ LIỆU THÔ
        # -------------------------------------------------------------
        if path == "/api/parse_xlsx":
            b64_data = payload.get("file_base64", "")
            if not b64_data:
                self._send_error(400, "Thiếu dữ liệu file Excel!")
                return
            try:
                if "," in b64_data:
                    b64_data = b64_data.split(",", 1)[1]
                raw_bytes = base64.b64decode(b64_data)
                parsed = parse_xlsx_bytes(raw_bytes)
                self._send_json({"status": "success", **parsed})
            except Exception as e:
                self._send_error(400, f"Không thể đọc tệp Excel: {str(e)}")
            return

        # -------------------------------------------------------------
        # XÁC THỰC ĐĂNG KÝ TÀI KHOẢN MỚI (SIGN UP / REGISTER)
        # -------------------------------------------------------------
        if path == "/api/register":
            name = payload.get("name", "").strip()
            email = payload.get("email", "").strip().lower()
            password = payload.get("password", "").strip()
            phone = payload.get("phone", "").strip()
            company = payload.get("company", "").strip() or "Doanh nghiệp B2B"
            role_code = payload.get("role_code", "CUSTOMER").strip()

            if not name or not email or not password:
                self._send_error(400, "Vui lòng điền đầy đủ Họ tên, Email và Mật khẩu!")
                return
            
            if len(password) < 6:
                self._send_error(400, "Mật khẩu phải có tối thiểu 6 ký tự để đảm bảo an toàn!")
                return

            if email in USER_DATABASE:
                self._send_error(400, f"Email '{email}' đã tồn tại trong hệ thống. Vui lòng đăng nhập hoặc sử dụng email khác!")
                return

            role_name_map = {
                "CUSTOMER": "Khách hàng Doanh nghiệp (B2B Client)",
                "SALES_REP": "Chuyên viên Kinh doanh B2B (Sales)",
                "SALES_MANAGER": "Trưởng phòng Kinh doanh B2B"
            }
            new_role_name = role_name_map.get(role_code, "Khách hàng Doanh nghiệp (B2B Client)")
            new_user_id = f"USR-{len(USER_DATABASE)+1:03d}"
            avatar_url = f"https://api.dicebear.com/7.x/adventurer/png?seed={name.replace(' ', '')}&backgroundColor=fef3c7"

            new_record = {
                "id": new_user_id,
                "email": email,
                "name": name,
                "phone": phone,
                "company": company,
                "password_hash": hash_password(password),
                "role_code": role_code,
                "role_name": new_role_name,
                "department": company,
                "avatar": avatar_url,
                "permissions": ["submit_request", "view_own_quotes"] if role_code == "CUSTOMER" else ["create_opp", "view_assigned_opps"]
            }

            USER_DATABASE[email] = new_record

            # Tự động đăng nhập và sinh phiên an toàn
            user_safe_info = {
                "id": new_record["id"],
                "name": new_record["name"],
                "email": new_record["email"],
                "phone": phone,
                "company": company,
                "role_code": new_record["role_code"],
                "role_name": new_record["role_name"],
                "department": new_record["department"],
                "avatar": new_record["avatar"],
                "permissions": new_record["permissions"]
            }
            token = _issue_session_token(user_safe_info)

            self._send_json({
                "status": "success",
                "token": token,
                "user": user_safe_info,
                "message": f"Chúc mừng {name}! Tài khoản của bạn đã được đăng ký và đăng nhập thành công."
            })
            return

        # -------------------------------------------------------------
        # CẬP NHẬT THÔNG TIN HỒ SƠ & ĐỔI MẬT KHẨU
        # -------------------------------------------------------------
        elif path == "/api/user/update_profile":
            user = self._get_authenticated_user()
            if not user:
                self._send_error(401, "Bạn chưa đăng nhập!")
                return
            
            email = user["email"]
            if email in USER_DATABASE:
                new_name = payload.get("name", user["name"]).strip()
                new_phone = payload.get("phone", user.get("phone", "")).strip()
                new_company = payload.get("company", user.get("company", "")).strip()
                
                USER_DATABASE[email]["name"] = new_name
                USER_DATABASE[email]["phone"] = new_phone
                USER_DATABASE[email]["company"] = new_company
                
                # Cập nhật session hiện tại
                user["name"] = new_name
                user["phone"] = new_phone
                user["company"] = new_company
                
                self._send_json({"status": "success", "user": user, "message": "Đã cập nhật thông tin hồ sơ thành công!"})
            else:
                self._send_error(404, "Không tìm thấy người dùng trong cơ sở dữ liệu!")
            return

        elif path == "/api/user/change_password":
            user = self._get_authenticated_user()
            if not user:
                self._send_error(401, "Bạn chưa đăng nhập!")
                return
            
            email = user["email"]
            old_pwd = payload.get("old_password", "").strip()
            new_pwd = payload.get("new_password", "").strip()
            
            if len(new_pwd) < 6:
                self._send_error(400, "Mật khẩu mới phải có tối thiểu 6 ký tự!")
                return
                
            if email in USER_DATABASE:
                if hash_password(old_pwd) != USER_DATABASE[email]["password_hash"]:
                    self._send_error(400, "Mật khẩu cũ không chính xác!")
                    return
                USER_DATABASE[email]["password_hash"] = hash_password(new_pwd)
                self._send_json({"status": "success", "message": "Đã đổi mật khẩu thành công!"})
            else:
                self._send_error(404, "Không tìm thấy người dùng!")
            return

        # -------------------------------------------------------------
        # XÁC THỰC ĐĂNG NHẬP CHÍNH XÁC (STRICT AUTHENTICATION)
        # -------------------------------------------------------------
        elif path == "/api/login":
            email = payload.get("email", "").strip().lower()
            password = payload.get("password", "").strip()

            if not email or not password:
                self._send_error(400, "Vui lòng nhập đầy đủ Email và Mật khẩu!")
                return

            # 1. Kiểm tra tài khoản có tồn tại không
            user_record = USER_DATABASE.get(email)
            if not user_record:
                self._send_error(401, f"Tài khoản '{email}' không tồn tại trong hệ thống B2B!")
                return

            # 2. Kiểm tra mật khẩu có khớp không
            input_hash = hash_password(password)
            if input_hash != user_record["password_hash"]:
                self._send_error(401, "Mật khẩu không chính xác! Vui lòng kiểm tra lại.")
                return

            # 3. Đăng nhập thành công -> Sinh token phiên làm việc
            user_safe_info = {
                "id": user_record["id"],
                "name": user_record["name"],
                "email": user_record["email"],
                "role_code": user_record["role_code"],
                "role_name": user_record["role_name"],
                "department": user_record["department"],
                "avatar": user_record["avatar"],
                "permissions": user_record["permissions"]
            }
            token = _issue_session_token(user_safe_info)

            self._send_json({
                "status": "success",
                "token": token,
                "user": user_safe_info,
                "message": f"Chào mừng {user_safe_info['name']} ({user_safe_info['role_name']})!"
            })
            return

        elif path == "/api/logout":
            token = payload.get("token")
            if token and token in ACTIVE_SESSIONS:
                del ACTIVE_SESSIONS[token]
            self._send_json({"status": "success", "message": "Đã đăng xuất an toàn khỏi hệ thống!"})
            return

        # -------------------------------------------------------------
        # NGHIỆP VỤ XỬ LÝ YÊU CẦU & KIỂM TRA PHÂN QUYỀN
        # -------------------------------------------------------------
        elif path == "/api/process_request":
            raw_text = payload.get("raw_text", "").strip()
            source = payload.get("source", "Email khách hàng")
            context = payload.get("context") or {}
            if not raw_text:
                self._send_error(400, "Nội dung yêu cầu không được để trống!")
                return

            new_opp = orchestrator.process_b2b_opportunity(raw_text, source, context=context)
            summary = orchestrator.get_dashboard_summary()
            self._send_json({
                "status": "success",
                "opportunity": new_opp,
                "summary": summary
            })
            return

        elif path == "/api/approve":
            user = self._get_authenticated_user()
            
            # KIỂM TRA PHÂN QUYỀN BẮT BUỘC: Chỉ Trưởng phòng hoặc Admin mới được duyệt
            if user and user["role_code"] not in ["SALES_MANAGER", "ADMIN"]:
                self._send_error(403, f"TỪ CHỐI TRUY CẬP: Bạn đang đăng nhập với vai trò '{user['role_name']}'. Chỉ Trưởng phòng Kinh doanh mới có thẩm quyền phê duyệt chiết khấu vượt hạn mức!")
                return

            opp_id = payload.get("opp_id")
            decision = payload.get("decision", "APPROVED")
            note = payload.get("note", "")
            opp_payload = payload.get("opportunity")

            # Đồng bộ cơ hội từ client nếu chưa có trong bộ nhớ backend
            if opp_payload and isinstance(opp_payload, dict):
                existing = [o for o in orchestrator.opportunities if o["id"] == opp_id]
                if not existing:
                    orchestrator.opportunities.insert(0, opp_payload)
                else:
                    idx = orchestrator.opportunities.index(existing[0])
                    orchestrator.opportunities[idx].update(opp_payload)

            approver_name = user["name"] if user else "Trưởng phòng Kinh doanh"
            note_with_approver = f"{note} (Ký duyệt bởi: {approver_name})"

            try:
                success = orchestrator.manager_decide_approval(opp_id, decision, note_with_approver)
                if success:
                    summary = orchestrator.get_dashboard_summary()
                    updated = [o for o in orchestrator.opportunities if o["id"] == opp_id][0]
                    self._send_json({
                        "status": "success",
                        "decision": decision,
                        "updated_opportunity": updated,
                        "summary": summary
                    })
                else:
                    self._send_error(404, "Không tìm thấy cơ hội bán hàng cần phê duyệt!")
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_error(500, f"Lỗi máy chủ khi phê duyệt: {str(e)}")
            return

        elif path == "/api/data_upload":
            user = self._get_authenticated_user()
            if user and user["role_code"] != "ADMIN":
                self._send_error(403, "Chỉ Quản trị viên (Admin) mới có quyền nạp và thay đổi dữ liệu Master Catalog!")
                return

            dataset_type = payload.get("type", "PRODUCT_CATALOG")
            items = payload.get("items", [])
            if dataset_type == "PRODUCT_CATALOG" and isinstance(items, list):
                for it in items:
                    sku = it.get("sku")
                    if sku:
                        orchestrator.catalog[sku] = it
                self._send_json({"status": "success", "message": f"Đã nạp thành công {len(items)} sản phẩm mới vào danh mục!"})
                return
            self._send_json({"status": "success", "message": "Dữ liệu đã được nạp thành công!"})
            return

        elif path in ["/api/reset_demo", "/api/clear_data", "/api/reset_data"]:
            orchestrator.reset_to_empty()
            summary = orchestrator.get_dashboard_summary()
            self._send_json({
                "status": "success",
                "message": "Đã làm sạch toàn bộ dữ liệu cơ hội và đưa hệ thống về trạng thái trống (Zero-state) thành công!",
                "summary": summary,
                "opportunities": orchestrator.opportunities
            })
            return

        elif path == "/api/seed_demo_data":
            count = orchestrator.seed_demo_opportunities()
            summary = orchestrator.get_dashboard_summary()
            self._send_json({
                "status": "success",
                "message": f"Đã nạp thành công {count} Test Case mẫu vào hệ thống!",
                "summary": summary,
                "opportunities": orchestrator.opportunities
            })
            return

        else:
            self._send_error(404, "API endpoint không tồn tại!")

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_error(self, code, message):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}, ensure_ascii=False).encode('utf-8'))

    def _generate_word_document(self, opp_list):
        rows = ""
        for o in opp_list:
            items_str = "<br>".join([f"• {it['name']} (SL: {it['requested_qty']}, Đơn giá: {it['unit_price']:,.0f} đ)" for it in o["validation"]["items"]])
            rows += f"""
            <tr>
                <td style="border:1px solid #ccc; padding:8px;"><b>{o['id']}</b><br>{o['created_at']}</td>
                <td style="border:1px solid #ccc; padding:8px;"><b>{o['customer_name']}</b><br>{o['contact_person']} ({o['email']})</td>
                <td style="border:1px solid #ccc; padding:8px;">{items_str}</td>
                <td style="border:1px solid #ccc; padding:8px;"><b>{o['pricing']['total_after_discount']:,.0f} đ</b><br><small>CK: {o['pricing']['discount_percentage']}%</small></td>
                <td style="border:1px solid #ccc; padding:8px;"><span style="color:#d9534f; font-weight:bold;">{o['status']}</span></td>
                <td style="border:1px solid #ccc; padding:8px;">{o['status_reason']}</td>
            </tr>
            """

        import datetime
        html = f"""
        <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
        <head><title>Báo Cáo Cơ Hội Bán Hàng B2B Doanh Nghiệp</title>
        <style>
            body {{ font-family: 'Times New Roman', serif; margin: 30px; }}
            h1 {{ color: #b45309; text-align: center; }}
            h2 {{ color: #333; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background: #fef3c7; border: 1px solid #ccc; padding: 10px; font-weight: bold; }}
        </style>
        </head>
        <body>
            <h1>HỆ THỐNG B2B AI AGENT - BÁO CÁO CƠ HỘI BÁN HÀNG DOANH NGHIỆP</h1>
            <p style="text-align:center; font-style: italic;">Hệ thống AI Agent Xử lý Cơ hội Bán hàng B2B | Ngày trích xuất: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <hr/>
            <h2>1. Danh Sách Cơ Hội Bán Hàng Được Xử Lý</h2>
            <table>
                <thead>
                    <tr>
                        <th>Mã Cơ Hội</th>
                        <th>Khách Hàng</th>
                        <th>Danh Mục Hàng Hóa</th>
                        <th>Tổng Giá Trị</th>
                        <th>Trạng Thái</th>
                        <th>Căn Cứ Nghiệp Vụ</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            <br/><br/>
            <table style="width:100%; border:none;">
                <tr>
                    <td style="text-align:center; width:50%;"><b>Chuyên Viên Kinh Doanh</b><br><br><br><br>(Ký và ghi rõ họ tên)</td>
                    <td style="text-align:center; width:50%;"><b>Trưởng Phòng Kinh Doanh</b><br><br><br><br><b>Lê Văn Tuấn</b></td>
                </tr>
            </table>
        </body>
        </html>
        """
        return html

class ReusableThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

def main():
    print(f"🚀 B2B Enterprise AI Agent Server (Bảo Mật & Phân Quyền) đang chạy tại: http://localhost:{PORT}")
    with ReusableThreadingServer(("0.0.0.0", PORT), B2BAgentHttpHandler) as httpd:
        print(f"✅ Sẵn sàng phục vụ tại http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
