"""
데이터베이스 연결 및 권한 테스트
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 환경 변수 로드
load_dotenv()

def test_supabase_connection():
    """Supabase 연결 테스트"""
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        print(f"🔗 Supabase URL: {url}")
        print(f"🔑 API Key: {key[:20]}...")
        
        # Supabase 클라이언트 생성
        supabase: Client = create_client(url, key)
        
        # 테이블 조회 테스트
        print("\n📊 테이블 조회 테스트:")
        
        # Users 테이블 조회
        try:
            result = supabase.table('users').select('*').limit(1).execute()
            print(f"✅ Users 테이블: {len(result.data)}개 레코드")
        except Exception as e:
            print(f"❌ Users 테이블 오류: {e}")
        
        # Ingredients 테이블 조회
        try:
            result = supabase.table('ingredients').select('*').limit(1).execute()
            print(f"✅ Ingredients 테이블: {len(result.data)}개 레코드")
        except Exception as e:
            print(f"❌ Ingredients 테이블 오류: {e}")
        
        # Recipes 테이블 조회
        try:
            result = supabase.table('recipes').select('*').limit(1).execute()
            print(f"✅ Recipes 테이블: {len(result.data)}개 레코드")
        except Exception as e:
            print(f"❌ Recipes 테이블 오류: {e}")
        
        # Meal_plans 테이블 조회
        try:
            result = supabase.table('meal_plans').select('*').limit(1).execute()
            print(f"✅ Meal_plans 테이블: {len(result.data)}개 레코드")
        except Exception as e:
            print(f"❌ Meal_plans 테이블 오류: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False

def test_user_creation():
    """사용자 생성 테스트"""
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        supabase: Client = create_client(url, key)
        
        print("\n👤 사용자 생성 테스트:")
        
        # 테스트 사용자 데이터
        test_user = {
            "email": "test@example.com",
            "name": "테스트 사용자"
        }
        
        # 기존 사용자 확인
        existing = supabase.table('users').select('*').eq('email', test_user['email']).execute()
        
        if existing.data:
            print(f"✅ 기존 사용자 발견: {existing.data[0]['name']}")
            return existing.data[0]['id']
        else:
            # 새 사용자 생성 시도
            result = supabase.table('users').insert(test_user).execute()
            
            if result.data:
                print(f"✅ 새 사용자 생성 성공: {result.data[0]['name']}")
                return result.data[0]['id']
            else:
                print("❌ 사용자 생성 실패: 데이터 없음")
                return None
                
    except Exception as e:
        print(f"❌ 사용자 생성 오류: {e}")
        return None

def suggest_solutions():
    """문제 해결 방안 제시"""
    print("\n💡 문제 해결 방안:")
    print("1. Supabase 대시보드에서 RLS (Row Level Security) 정책 확인")
    print("2. 테이블의 INSERT, SELECT 권한 설정 확인")
    print("3. anon 키 대신 service_role 키 사용 고려")
    print("4. 테스트 모드로 로컬 데이터 사용")
    
    print("\n🔧 임시 해결책:")
    print("- config.py에서 TEST_MODE = True로 설정")
    print("- 또는 Supabase 대시보드에서 RLS 정책 비활성화")

if __name__ == "__main__":
    print("🧪 데이터베이스 연결 테스트")
    print("=" * 50)
    
    # 연결 테스트
    if test_supabase_connection():
        # 사용자 생성 테스트
        user_id = test_user_creation()
        
        if user_id:
            print(f"\n🎉 모든 테스트 통과! 사용자 ID: {user_id}")
        else:
            suggest_solutions()
    else:
        print("\n❌ 기본 연결에 실패했습니다.")
        suggest_solutions()