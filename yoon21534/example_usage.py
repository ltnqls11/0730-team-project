"""
스마트 냉장고 - Supabase 클라이언트 사용 예시

이 파일은 Supabase Python 클라이언트를 사용하여 데이터베이스와 상호작용하는 방법을 보여줍니다.
"""

from database import SmartFridgeDB
from datetime import date, timedelta
import os

def example_usage():
    """Supabase 클라이언트 사용 예시"""
    
    # 데이터베이스 연결
    db = SmartFridgeDB()
    
    # 1. 사용자 생성 및 조회
    print("=== 사용자 관리 ===")
    
    # 새 사용자 생성
    user_id = db.create_user("test@example.com", "테스트 사용자")
    print(f"생성된 사용자 ID: {user_id}")
    
    # 사용자 조회
    found_user_id = db.get_user_id("test@example.com")
    print(f"조회된 사용자 ID: {found_user_id}")
    
    # 2. 식재료 관리
    print("\n=== 식재료 관리 ===")
    
    # 식재료 추가
    success = db.add_ingredient(
        user_id=user_id,
        name="양파",
        quantity=2.0,
        unit="개",
        purchase_date=date.today(),
        expiry_date=date.today() + timedelta(days=7),
        category="채소",
        location="냉장고"
    )
    print(f"양파 추가 성공: {success}")
    
    # 식재료 추가 (유통기한 임박)
    success = db.add_ingredient(
        user_id=user_id,
        name="우유",
        quantity=1.0,
        unit="L",
        purchase_date=date.today() - timedelta(days=5),
        expiry_date=date.today() + timedelta(days=2),
        category="유제품",
        location="냉장고"
    )
    print(f"우유 추가 성공: {success}")
    
    # 모든 식재료 조회
    ingredients = db.get_ingredients(user_id)
    print(f"총 식재료 수: {len(ingredients)}")
    for ingredient in ingredients:
        print(f"- {ingredient['name']}: {ingredient['quantity']}{ingredient['unit']} (만료: {ingredient['expiry_date']})")
    
    # 유통기한 임박 식재료 조회
    expiring_ingredients = db.get_expiring_ingredients(user_id, 3)
    print(f"유통기한 임박 식재료: {len(expiring_ingredients)}개")
    for ingredient in expiring_ingredients:
        print(f"- {ingredient['name']} (만료: {ingredient['expiry_date']})")
    
    # 3. 레시피 관리
    print("\n=== 레시피 관리 ===")
    
    # 레시피 추가
    success = db.add_recipe(
        user_id=user_id,
        name="김치찌개",
        description="맛있는 김치찌개 만드는 방법",
        ingredients_list="김치 200g, 돼지고기 100g, 두부 1/2모, 양파 1/2개",
        cooking_time=30,
        difficulty="중급",
        category="한식"
    )
    print(f"김치찌개 레시피 추가 성공: {success}")
    
    # 레시피 조회
    recipes = db.get_recipes(user_id)
    print(f"총 레시피 수: {len(recipes)}")
    for recipe in recipes:
        print(f"- {recipe['name']} ({recipe['category']}): {recipe['cooking_time']}분")
    
    # 4. 식단 계획
    print("\n=== 식단 계획 ===")
    
    if recipes:
        recipe_id = recipes[0]['id']
        
        # 식단 계획 추가
        success = db.add_meal_plan(
            user_id=user_id,
            recipe_id=recipe_id,
            plan_date=date.today() + timedelta(days=1),
            meal_type="저녁",
            notes="가족과 함께 먹을 저녁"
        )
        print(f"식단 계획 추가 성공: {success}")
        
        # 식단 계획 조회
        meal_plans = db.get_meal_plans(user_id, date.today(), date.today() + timedelta(days=7))
        print(f"이번 주 식단 계획: {len(meal_plans)}개")
        for plan in meal_plans:
            recipe_name = plan['recipes']['name'] if plan['recipes'] else "레시피 없음"
            print(f"- {plan['plan_date']} {plan['meal_type']}: {recipe_name}")
    
    # 5. 통계 정보
    print("\n=== 통계 정보 ===")
    
    stats = db.get_ingredient_statistics(user_id)
    print(f"총 식재료: {stats['total']}개")
    print(f"만료된 재료: {stats['expired']}개")
    print(f"유통기한 임박: {stats['expiring_soon']}개")
    print(f"카테고리: {len(stats['categories'])}개")
    
    for category, count in stats['categories'].items():
        print(f"- {category}: {count}개")

def test_connection():
    """Supabase 연결 테스트"""
    try:
        db = SmartFridgeDB()
        print("✅ Supabase 연결 성공!")
        return True
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False

if __name__ == "__main__":
    print("스마트 냉장고 - Supabase 클라이언트 사용 예시")
    print("=" * 50)
    
    # 연결 테스트
    if test_connection():
        example_usage()
    else:
        print("환경 변수를 확인해주세요:")
        print("- SUPABASE_URL")
        print("- SUPABASE_KEY") 