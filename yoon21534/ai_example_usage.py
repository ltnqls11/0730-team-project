"""
🤖 AI 스마트 냉장고 - 사용 예제

이 파일은 새로운 AI 기능들의 사용 예제를 보여줍니다.
"""

import os
from datetime import date, timedelta
from ai_services import SmartFridgeAI
from database import SmartFridgeDB

def example_ai_recipe_recommendation():
    """AI 레시피 추천 예제"""
    print("🍳 AI 레시피 추천 예제")
    print("=" * 50)
    
    # AI 서비스 초기화
    ai = SmartFridgeAI()
    
    # 예제 재료 데이터
    sample_ingredients = [
        {"name": "양파", "quantity": 2, "unit": "개"},
        {"name": "돼지고기", "quantity": 300, "unit": "g"},
        {"name": "김치", "quantity": 200, "unit": "g"},
        {"name": "두부", "quantity": 1, "unit": "모"}
    ]
    
    # 식단 선호도
    dietary_preferences = "매운 음식 선호, 한식 위주"
    
    try:
        # AI 레시피 추천 실행
        recipes = ai.recommend_recipes(sample_ingredients, dietary_preferences)
        
        print(f"✅ {len(recipes)}개의 레시피를 추천받았습니다!")
        
        for i, recipe in enumerate(recipes, 1):
            print(f"\n📖 레시피 {i}: {recipe['name']}")
            print(f"   카테고리: {recipe['category']}")
            print(f"   조리시간: {recipe['cooking_time']}분")
            print(f"   난이도: {recipe['difficulty']}")
            print(f"   설명: {recipe['description']}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def example_smart_meal_planning():
    """스마트 식단 계획 예제"""
    print("\n📅 스마트 식단 계획 예제")
    print("=" * 50)
    
    ai = SmartFridgeAI()
    
    # 예제 설정
    days = 3
    dietary_goals = "건강한 다이어트, 저칼로리 식단"
    available_ingredients = [
        {"name": "닭가슴살"}, {"name": "브로콜리"}, 
        {"name": "현미"}, {"name": "계란"}
    ]
    
    try:
        meal_plan = ai.create_meal_plan(days, dietary_goals, available_ingredients)
        
        if meal_plan and 'meal_plan' in meal_plan:
            print(f"✅ {days}일간의 식단 계획이 생성되었습니다!")
            
            for day_key, day_plan in meal_plan['meal_plan'].items():
                day_num = day_key.split('_')[1]
                print(f"\n📅 {day_num}일차:")
                
                for meal_type, meal_info in day_plan.items():
                    print(f"   {meal_type}: {meal_info['name']} ({meal_info['calories']}kcal)")
            
            if 'shopping_list' in meal_plan:
                print(f"\n🛒 쇼핑 리스트: {', '.join(meal_plan['shopping_list'])}")
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def example_nutrition_analysis():
    """영양 분석 예제"""
    print("\n🥗 영양 분석 예제")
    print("=" * 50)
    
    ai = SmartFridgeAI()
    
    # 예제 식단 데이터
    sample_meal_plan = [
        {"meal_type": "아침", "recipe_name": "계란후라이와 토스트"},
        {"meal_type": "점심", "recipe_name": "닭가슴살 샐러드"},
        {"meal_type": "저녁", "recipe_name": "현미밥과 된장찌개"}
    ]
    
    try:
        analysis = ai.analyze_nutrition(sample_meal_plan)
        
        if analysis:
            print("✅ 영양 분석 완료!")
            print(f"   건강 점수: {analysis.get('health_score', 'N/A')}/10")
            print(f"   총 칼로리: {analysis.get('total_calories', 'N/A')}kcal")
            
            if 'recommendations' in analysis:
                print("   💡 개선 방안:")
                for rec in analysis['recommendations'][:3]:
                    print(f"      - {rec}")
                    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def example_cooking_assistant():
    """요리 도우미 예제"""
    print("\n👨‍🍳 요리 도우미 예제")
    print("=" * 50)
    
    ai = SmartFridgeAI()
    
    recipe_name = "김치찌개"
    current_step = 3
    
    try:
        # 요리 도움말 받기
        advice = ai.get_cooking_assistant(recipe_name, current_step)
        print(f"✅ {recipe_name} {current_step}단계 조언:")
        print(f"   {advice}")
        
        # 재료 대체 추천
        missing_ingredient = "돼지고기"
        substitutes = ai.suggest_ingredient_substitutes(missing_ingredient, recipe_name)
        
        if substitutes:
            print(f"\n🔄 {missing_ingredient} 대체재 추천:")
            for sub in substitutes[:3]:
                print(f"   - {sub['substitute']}: {sub['reason']}")
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def example_database_integration():
    """데이터베이스 연동 예제"""
    print("\n🗄️ 데이터베이스 연동 예제")
    print("=" * 50)
    
    try:
        db = SmartFridgeDB()
        
        # 테스트 사용자 생성
        user_id = db.create_user("test@example.com", "테스트 사용자")
        
        if user_id:
            print(f"✅ 사용자 생성 완료: {user_id[:8]}...")
            
            # 재료 추가
            success = db.add_ingredient(
                user_id, "양파", 2, "개",
                date.today(), date.today() + timedelta(days=7),
                "채소", "냉장고"
            )
            
            if success:
                print("✅ 재료 추가 완료")
                
                # 재료 조회
                ingredients = db.get_ingredients(user_id)
                print(f"📦 등록된 재료: {len(ingredients)}개")
                
                # 통계 조회
                stats = db.get_ingredient_statistics(user_id)
                print(f"📊 통계: 총 {stats['total']}개, 임박 {stats['expiring_soon']}개")
                
    except Exception as e:
        print(f"❌ 데이터베이스 오류: {e}")

def main():
    """메인 실행 함수"""
    print("🤖 AI 스마트 냉장고 - 사용 예제")
    print("=" * 60)
    
    # OpenAI API 키 확인
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  경고: OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 API 키를 설정해주세요.")
        return
    
    # 각 기능 예제 실행
    try:
        example_ai_recipe_recommendation()
        example_smart_meal_planning()
        example_nutrition_analysis()
        example_cooking_assistant()
        example_database_integration()
        
        print("\n🎉 모든 예제가 완료되었습니다!")
        print("📖 자세한 사용법은 AI_FEATURES_GUIDE.md를 참고하세요.")
        
    except KeyboardInterrupt:
        print("\n⏹️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    main()