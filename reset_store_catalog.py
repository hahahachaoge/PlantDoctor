import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("smart_agri.db")


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("UPDATE store_products SET sold_count = 0")
    cur.execute("UPDATE store_products SET category = '精选好物', sub_category = '精选' WHERE id IN (2001, 2002, 2003, 2004, 2005)")
    cur.execute("UPDATE store_products SET category = '热销榜单', sub_category = '热销' WHERE id IN (2101, 2102, 2103, 2104, 2105)")
    cur.execute("UPDATE store_products SET category = '肥料', sub_category = '肥料' WHERE id IN (2201, 2202, 2203, 2204, 2205, 2206)")
    cur.execute("UPDATE store_products SET category = '杀虫剂', sub_category = '杀虫剂' WHERE id IN (2301, 2302, 2303, 2304, 2305, 2306)")
    cur.execute("UPDATE store_products SET category = '商城首页', sub_category = '广告' WHERE id = 2401")
    cur.execute("UPDATE store_products SET category = '热销榜单', sub_category = '热销榜单' WHERE id IN (2402, 2403, 2404, 2405)")
    cur.execute("UPDATE store_products SET category = '肥料', sub_category = '肥料推荐' WHERE id IN (2406, 2407)")
    cur.execute("UPDATE store_products SET category = '杀虫剂', sub_category = '杀虫剂推荐' WHERE id IN (2408, 2409)")

    conn.commit()

    print("non_zero_sold_count:", cur.execute("SELECT COUNT(*) FROM store_products WHERE sold_count <> 0").fetchone()[0])
    print("hot:")
    for row in cur.execute(
        "SELECT id, name, specification, price, sold_count FROM store_products WHERE sub_category = '热销榜单' ORDER BY id"
    ):
        print(row)
    print("fertilizer:")
    for row in cur.execute(
        "SELECT id, name, specification, price, sold_count FROM store_products WHERE sub_category = '肥料推荐' ORDER BY id"
    ):
        print(row)
    print("pesticide:")
    for row in cur.execute(
        "SELECT id, name, specification, price, sold_count FROM store_products WHERE sub_category = '杀虫剂推荐' ORDER BY id"
    ):
        print(row)

    conn.close()


if __name__ == "__main__":
    main()
