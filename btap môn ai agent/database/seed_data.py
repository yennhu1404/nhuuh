import random
import datetime
from database.db_engine import DWHDatabaseEngine

def seed_enterprise_dwh():
    engine = DWHDatabaseEngine()
    
    # Drop and recreate schema
    init_sql = """
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS stores;
    DROP TABLE IF EXISTS inventory_alerts;

    CREATE TABLE stores (
        store_id VARCHAR(20) PRIMARY KEY,
        store_name VARCHAR(100) NOT NULL,
        region VARCHAR(50) NOT NULL,
        manager_id VARCHAR(50) NOT NULL
    );

    CREATE TABLE orders (
        order_id VARCHAR(50) PRIMARY KEY,
        store_id VARCHAR(20),
        order_date TEXT NOT NULL,
        order_hour INTEGER NOT NULL,
        status VARCHAR(20) NOT NULL,
        total_amount REAL NOT NULL,
        customer_phone VARCHAR(20),
        customer_name VARCHAR(100),
        is_test INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE inventory_alerts (
        alert_id VARCHAR(50) PRIMARY KEY,
        store_id VARCHAR(20) NOT NULL,
        sku_id VARCHAR(50) NOT NULL,
        alert_time TEXT NOT NULL,
        alert_reason TEXT NOT NULL
    );
    """
    engine.execute_script(init_sql)

    # 1. Seed Stores
    stores_data = [
        ("STORE_01", "Cửa hàng #01 - Ba Đình (HN)", "North", "MGR_NORTH_01"),
        ("STORE_02", "Cửa hàng #02 - Cầu Giấy (HN)", "North", "MGR_NORTH_02"),
        ("STORE_03", "Cửa hàng #03 - Hải Phòng", "North", "MGR_NORTH_03"),
        ("STORE_04", "Cửa hàng #04 - Đống Đa (HN)", "North", "MGR_NORTH_04"),
        ("STORE_05", "Cửa hàng #05 - Quận 1 (SG)", "South", "MGR_SOUTH_01"),
        ("STORE_06", "Cửa hàng #06 - Bình Thạnh (SG)", "South", "MGR_SOUTH_02"),
        ("STORE_07", "Cửa hàng #07 - Hà Đông (HN)", "North", "MGR_NORTH_05"),
    ]
    with engine.get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("INSERT INTO stores VALUES (?, ?, ?, ?)", stores_data)
        conn.commit()

    # 2. Seed Orders for Yesterday
    # Realistic dates: yesterday
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    
    orders_data = []
    order_counter = 1000

    # Store configurations: (store_id, total_orders, target_cancel_pct)
    # Store #04: target cancel rate ~ 18.4%
    store_profiles = [
        ("STORE_01", 300, 0.05),
        ("STORE_02", 280, 0.06),
        ("STORE_03", 250, 0.07),
        ("STORE_04", 320, 0.184), # Target store in scenario
        ("STORE_05", 350, 0.04), # South
        ("STORE_06", 310, 0.06), # South
        ("STORE_07", 260, 0.08),
    ]

    for store_id, total, cancel_ratio in store_profiles:
        num_cancels = int(total * cancel_ratio)
        num_completed = total - num_cancels

        # Generate cancelled orders
        for _ in range(num_cancels):
            order_counter += 1
            if store_id == "STORE_04":
                # 82% of cancellations at Store #04 happen during 17h-19h peak
                if random.random() < 0.82:
                    hour = random.choice([17, 18, 19])
                else:
                    hour = random.choice([9, 10, 11, 14, 15, 20])
            else:
                hour = random.randint(8, 21)

            orders_data.append((
                f"ORD_{yesterday}_{order_counter}",
                store_id,
                f"{yesterday} {hour:02d}:{random.randint(0,59):02d}:00",
                hour,
                "cancelled",
                round(random.uniform(150000, 850000), 2),
                f"09{random.randint(10000000, 99999999)}",
                f"Khách hàng {order_counter}",
                0
            ))

        # Generate completed orders
        for _ in range(num_completed):
            order_counter += 1
            hour = random.randint(8, 21)
            orders_data.append((
                f"ORD_{yesterday}_{order_counter}",
                store_id,
                f"{yesterday} {hour:02d}:{random.randint(0,59):02d}:00",
                hour,
                "completed",
                round(random.uniform(120000, 1200000), 2),
                f"09{random.randint(10000000, 99999999)}",
                f"Khách hàng {order_counter}",
                0
            ))

    # 3. Inject Test Orders (14 test orders with is_test = 1 as in Demo Case)
    for i in range(14):
        order_counter += 1
        orders_data.append((
            f"ORD_TEST_{yesterday}_{order_counter}",
            "STORE_04" if i % 2 == 0 else "STORE_01",
            f"{yesterday} 10:00:00",
            10,
            "cancelled" if i % 3 == 0 else "completed",
            0.0,
            "0900000000",
            "Tester Nội Bộ IT",
            1  # is_test = 1
        ))

    # 4. Inject Dirty Records to test Data Quarantine (Anomaly Detection)
    # Record with negative amount
    order_counter += 1
    orders_data.append((
        f"ORD_DIRTY_NEG_{order_counter}",
        "STORE_02",
        f"{yesterday} 11:30:00",
        11,
        "completed",
        -250000.0, # Negative revenue
        "0912345678",
        "KH Bất Thường",
        0
    ))

    # Record with NULL store_id
    order_counter += 1
    orders_data.append((
        f"ORD_DIRTY_NULL_{order_counter}",
        None, # Missing store_id
        f"{yesterday} 14:15:00",
        14,
        "completed",
        150000.0,
        "0912345679",
        "KH Thiếu Store",
        0
    ))

    # Insert orders
    with engine.get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", orders_data)
        conn.commit()

    # 5. Seed Inventory Alerts for Store #04
    alerts = [
        ("ALT_001", "STORE_04", "SKU_BEV_01", f"{yesterday} 17:15:00", "Lệch tồn kho thực tế - POS chưa đồng bộ kịp (tồn ảo 12 ly)"),
        ("ALT_002", "STORE_04", "SKU_BEV_03", f"{yesterday} 17:45:00", "Lệch tồn kho thực tế - Nguyên liệu trà sữa hết nhưng POS còn nhận đơn"),
        ("ALT_003", "STORE_04", "SKU_FOOD_08", f"{yesterday} 18:30:00", "Đơn hàng bị hủy do nhân viên bấm từ chối vì hết bánh ngọt trên quầy"),
    ]
    with engine.get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("INSERT INTO inventory_alerts VALUES (?, ?, ?, ?, ?)", alerts)
        conn.commit()

    print(f"✅ Seeding completed! Total {len(orders_data)} orders created for yesterday ({yesterday}).")

if __name__ == "__main__":
    seed_enterprise_dwh()

