import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect('database.db')  # 실제 파일명으로 변경
cursor = conn.cursor()

# 컬럼 추가
try:
    cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    conn.commit()
    print("password_hash 컬럼이 추가되었습니다.")
except sqlite3.OperationalError as e:
    print(f"오류: {e}")

conn.close()