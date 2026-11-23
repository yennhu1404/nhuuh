"""
B2B Product Catalog & Business Policies for Minh An Company
Dữ liệu danh mục sản phẩm chính thức, tồn kho khả dụng, thời gian giao hàng và chính sách phê duyệt chiết khấu.
"""

# 1. Danh mục sản phẩm chính thức của Minh An Company
OFFICIAL_CATALOG = {
    "PRD-LAP-001": {
        "sku": "PRD-LAP-001",
        "name": "Laptop Doanh Nghiệp Dell Vostro 5630",
        "category": "Thiết bị văn phòng",
        "unit_price": 18500000,  # 18.5 triệu VNĐ
        "stock_available": 45,
        "standard_lead_days": 3,
        "express_lead_days": 1,
        "warranty_months": 24,
        "aliases": ["dell vostro", "laptop dell", "dell vostro 5630", "máy tính xách tay dell"]
    },
    "PRD-LAP-002": {
        "sku": "PRD-LAP-002",
        "name": "Laptop Lenovo ThinkPad E14 Gen 5",
        "category": "Thiết bị văn phòng",
        "unit_price": 21000000,
        "stock_available": 30,
        "standard_lead_days": 3,
        "express_lead_days": 1,
        "warranty_months": 36,
        "aliases": ["thinkpad", "lenovo thinkpad", "thinkpad e14", "laptop lenovo"]
    },
    "PRD-MON-001": {
        "sku": "PRD-MON-001",
        "name": "Màn hình Dell P2422H 23.8 inch IPS Full HD",
        "category": "Màn hình hiển thị",
        "unit_price": 4200000,
        "stock_available": 60,
        "standard_lead_days": 2,
        "express_lead_days": 1,
        "warranty_months": 36,
        "aliases": ["màn hình dell", "dell p2422h", "màn hình 24 inch", "monitor dell"]
    },
    "PRD-SVR-001": {
        "sku": "PRD-SVR-001",
        "name": "Máy chủ Server Dell PowerEdge R450 Rack 1U",
        "category": "Hạ tầng & Máy chủ",
        "unit_price": 68000000,
        "stock_available": 8,
        "standard_lead_days": 7,
        "express_lead_days": 3,
        "warranty_months": 36,
        "aliases": ["server dell", "dell poweredge", "poweredge r450", "máy chủ dell", "máy chủ server"]
    },
    "PRD-NET-001": {
        "sku": "PRD-NET-001",
        "name": "Thiết bị định tuyến Router Cisco Catalyst C8200L",
        "category": "Thiết bị mạng",
        "unit_price": 24500000,
        "stock_available": 30,
        "standard_lead_days": 5,
        "express_lead_days": 2,
        "warranty_months": 12,
        "aliases": ["router cisco", "cisco catalyst", "c8200l", "router cisco catalyst"]
    },
    "PRD-NET-002": {
        "sku": "PRD-NET-002",
        "name": "Switch mạng Cisco Catalyst 24 Port Gigabit C1000-24T",
        "category": "Thiết bị mạng",
        "unit_price": 14000000,
        "stock_available": 25,
        "standard_lead_days": 4,
        "express_lead_days": 2,
        "warranty_months": 24,
        "aliases": ["switch cisco", "switch c1000", "switch 24 port", "switch mạng cisco"]
    },
    "PRD-PRN-001": {
        "sku": "PRD-PRN-001",
        "name": "Máy in Laser đa năng HP LaserJet Pro MFP M428fdw",
        "category": "Thiết bị văn phòng",
        "unit_price": 11500000,
        "stock_available": 12,
        "standard_lead_days": 14,  # Hiện tại kho ít hàng, cần 14 ngày nhập thêm
        "express_lead_days": 10,
        "warranty_months": 12,
        "aliases": ["máy in hp", "hp laserjet", "m428fdw", "máy in laser"]
    },
    "PRD-CAM-001": {
        "sku": "PRD-CAM-001",
        "name": "Camera hội nghị trực tuyến Logitech Rally Bar Mini",
        "category": "Thiết bị hội nghị",
        "unit_price": 48000000,
        "stock_available": 15,
        "standard_lead_days": 5,
        "express_lead_days": 2,
        "warranty_months": 24,
        "aliases": ["camera hội nghị", "logitech rally", "rally bar mini", "logitech rally bar"]
    },
    "SW-24P-01": {
        "sku": "SW-24P-01",
        "name": "Switch 24 port",
        "category": "Switch",
        "unit_price": 8500000,
        "unit_cost": 6800000,
        "stock_available": 120,
        "standard_lead_days": 3,
        "express_lead_days": 1,
        "warranty_months": 12,
        "aliases": ["sw-24p-01"]
    },
    "SW-48P-01": {
        "sku": "SW-48P-01",
        "name": "Switch 48 port",
        "category": "Switch",
        "unit_price": 18000000,
        "unit_cost": 14000000,
        "stock_available": 80,
        "standard_lead_days": 3,
        "express_lead_days": 1,
        "warranty_months": 12,
        "aliases": ["sw-48p-01", "switch 48 port"]
    },
    "RT-EDGE-01": {
        "sku": "RT-EDGE-01",
        "name": "Router Edge 1G",
        "category": "Router",
        "unit_price": 12000000,
        "unit_cost": 9000000,
        "stock_available": 60,
        "standard_lead_days": 4,
        "express_lead_days": 2,
        "warranty_months": 12,
        "aliases": ["rt-edge-01", "router edge 1g"]
    },
    "AP-W6-01": {
        "sku": "AP-W6-01",
        "name": "Access Point Wi-Fi 6",
        "category": "Access Point",
        "unit_price": 4200000,
        "unit_cost": 3200000,
        "stock_available": 200,
        "standard_lead_days": 3,
        "express_lead_days": 1,
        "warranty_months": 12,
        "aliases": ["ap-w6-01", "access point wi-fi 6", "access point wifi 6"]
    },
    "FW-EDGE-01": {
        "sku": "FW-EDGE-01",
        "name": "Firewall Edge",
        "category": "Firewall",
        "unit_price": 32000000,
        "unit_cost": 25000000,
        "stock_available": 40,
        "standard_lead_days": 5,
        "express_lead_days": 2,
        "warranty_months": 12,
        "aliases": ["fw-edge-01", "firewall edge", "firewall"]
    }
}

# 2. Danh sách 6 nhân viên kinh doanh Minh An Company
SALES_REPRESENTATIVES = [
    {"id": "SALES-01", "name": "Nguyễn Văn An", "email": "an.nguyen@minhan.com.vn", "role": "Senior Sales B2B"},
    {"id": "SALES-02", "name": "Trần Thị Bình", "email": "binh.tran@minhan.com.vn", "role": "Sales Representative"},
    {"id": "SALES-03", "name": "Lê Hoàng Long", "email": "long.le@minhan.com.vn", "role": "Key Account Manager"},
    {"id": "SALES-04", "name": "Phạm Minh Đức", "email": "duc.pham@minhan.com.vn", "role": "Sales Representative"},
    {"id": "SALES-05", "name": "Đỗ Mai Lan", "email": "lan.do@minhan.com.vn", "role": "Enterprise Sales"},
    {"id": "SALES-06", "name": "Vũ Quốc Huy", "email": "huy.vu@minhan.com.vn", "role": "Sales Representative"}
]

# 3. Phân quyền và Quy tắc phê duyệt chiết khấu
DISCOUNT_APPROVAL_POLICY = {
    "sales_rep_max_discount": 5.0,  # <= 5.0%: Thuộc thẩm quyền Nhân viên Kinh doanh
    "sales_manager_max_discount": 15.0,  # > 5.0% và <= 15.0%: Thẩm quyền Trưởng phòng Kinh doanh
    "director_min_discount": 15.0,  # > 15.0%: Thẩm quyền Ban Giám Đốc
    "high_value_contract_threshold": 500000000,  # >= 500 triệu VNĐ cần Trưởng phòng duyệt dù chiết khấu nhỏ
    "manager_name": "Lê Văn Tuấn",
    "manager_title": "Trưởng phòng Kinh doanh B2B",
    "manager_email": "tuan.le@minhan.com.vn"
}
