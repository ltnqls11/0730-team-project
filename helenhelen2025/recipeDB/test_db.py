#!/usr/bin/env python3
"""
sb-2.py의 데이터베이스 연동을 테스트하는 스크립트
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

def test_database_connection():
    """데이터베이스 연결 테스트"""
    try:
        conn = sqlite3.connect("fridge_management.db", timeout=30.0)
        conn.text_factory = str
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("✅ 데이터베이스 연결 성공!")
        print(f"📋 테이블 목록: {[table[0] for table in tables]}")
        
        # 각 테이블의 레코드 수 확인
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count}개 레코드")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {str(e)}")
        return False

def test_ingredient_operations():
    """재료 관련 작업 테스트"""
    try:
        conn = sqlite3.connect("fridge_management.db", timeout=30.0)
        conn.text_factory = str
        cursor = conn.cursor()
        
        # 테스트 재료 추가
        test_ingredient = ("테스트재료", "기타", 1.0, "개", (datetime.now() + timedelta(days=5)).date())
        cursor.execute('''
            INSERT INTO ingredients (name, category, quantity, unit, expiry_date)
            VALUES (?, ?, ?, ?, ?)
        ''', test_ingredient)
        
        # 재료 조회
        cursor.execute("SELECT * FROM ingredients WHERE name = '테스트재료'")
        result = cursor.fetchone()
        
        if result:
            print("✅ 재료 추가/조회 성공!")
            print(f"   추가된 재료: {result}")
            
            # 테스트 재료 삭제
            cursor.execute("DELETE FROM ingredients WHERE name = '테스트재료'")
            print("✅ 재료 삭제 성공!")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 재료 작업 테스트 실패: {str(e)}")
        return False

def test_pandas_integration():
    """Pandas 연동 테스트"""
    try:
        conn = sqlite3.connect("fridge_management.db", timeout=30.0)
        
        # 재료 데이터 조회
        df = pd.read_sql_query('''
            SELECT * FROM ingredients 
            ORDER BY 
                CASE WHEN expiry_date IS NULL THEN 1 ELSE 0 END,
                expiry_date ASC, 
                name ASC
        ''', conn)
        
        print("✅ Pandas 연동 성공!")
        print(f"   조회된 재료 수: {len(df)}")
        
        if not df.empty:
            print("   첫 번째 재료:")
            print(f"   - 이름: {df.iloc[0]['name']}")
            print(f"   - 카테고리: {df.iloc[0]['category']}")
            print(f"   - 수량: {df.iloc[0]['quantity']} {df.iloc[0]['unit']}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Pandas 연동 테스트 실패: {str(e)}")
        return False

def main():
    print("🔍 sb-2.py 데이터베이스 연동 테스트 시작\n")
    
    # 데이터베이스 파일 존재 확인
    if os.path.exists("fridge_management.db"):
        print("📁 데이터베이스 파일 존재 확인")
    else:
        print("⚠️  데이터베이스 파일이 없습니다. 새로 생성됩니다.")
    
    # 테스트 실행
    tests = [
        ("데이터베이스 연결", test_database_connection),
        ("재료 작업", test_ingredient_operations),
        ("Pandas 연동", test_pandas_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name} 테스트 중...")
        result = test_func()
        results.append((test_name, result))
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 테스트 결과 요약")
    print("="*50)
    
    for test_name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name}: {status}")
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    if success_count == total_count:
        print(f"\n🎉 모든 테스트 통과! ({success_count}/{total_count})")
        print("sb-2.py를 실행할 준비가 되었습니다.")
    else:
        print(f"\n⚠️  일부 테스트 실패 ({success_count}/{total_count})")
        print("문제를 해결한 후 다시 시도해주세요.")

if __name__ == "__main__":
    main()