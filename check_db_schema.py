import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect('ltnqls11/recipe_management.db')
cursor = conn.cursor()

# Users 테이블 스키마 확인
cursor.execute("PRAGMA table_info(Users)")
columns = cursor.fetchall()

print("Users 테이블 스키마:")
for column in columns:
    print(f"  {column[1]} {column[2]} {'NOT NULL' if column[3] else ''} {'PRIMARY KEY' if column[5] else ''}")

# 테이블 존재 여부 확인
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Users'")
table_exists = cursor.fetchone()

if table_exists:
    print("\nUsers 테이블이 존재합니다.")
else:
    print("\nUsers 테이블이 존재하지 않습니다.")

conn.close()