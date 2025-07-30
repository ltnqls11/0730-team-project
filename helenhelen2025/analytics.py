import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import numpy as np
from typing import List, Dict
import json

class FoodAnalytics:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_ingredient_category_distribution(self):
        """재료 카테고리별 분포"""
        ingredients = self.db_manager.get_ingredients()
        if not ingredients:
            return None
        
        category_counts = {}
        for ing in ingredients:
            category = ing.get('category', '기타')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return category_counts
    
    def get_recipe_difficulty_stats(self):
        """레시피 난이도별 통계"""
        recipes = self.db_manager.get_recipes()
        if not recipes:
            return None
        
        difficulty_counts = {}
        for recipe in recipes:
            difficulty = recipe.get('difficulty_level', '보통')
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        return difficulty_counts
    
    def get_cooking_frequency_by_month(self):
        """월별 요리 빈도"""
        try:
            result = self.db_manager.supabase.table("cooking_history").select("cooked_date").execute()
            if not result.data:
                return None
            
            monthly_counts = {}
            for record in result.data:
                try:
                    date_obj = datetime.strptime(record['cooked_date'][:10], '%Y-%m-%d')
                    month_key = date_obj.strftime('%Y-%m')
                    monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
                except:
                    continue
            
            return monthly_counts
        except:
            return None
    
    def get_ingredient_usage_efficiency(self):
        """재료 활용 효율성"""
        ingredients = self.db_manager.get_ingredients()
        recipes = self.db_manager.get_recipes()
        
        if not ingredients or not recipes:
            return None
        
        # 재료별 사용 빈도 계산
        ingredient_usage = {}
        for recipe in recipes:
            recipe_detail = self.db_manager.get_recipe_with_ingredients(recipe['id'])
            if recipe_detail and 'ingredients' in recipe_detail:
                for ing in recipe_detail['ingredients']:
                    ing_name = ing.get('ingredient_name', '')
                    usage_count = recipe.get('usage_count', 0)
                    ingredient_usage[ing_name] = ingredient_usage.get(ing_name, 0) + usage_count
        
        # 보유 재료와 비교
        total_ingredients = len(ingredients)
        used_ingredients = len(ingredient_usage)
        efficiency = (used_ingredients / total_ingredients * 100) if total_ingredients > 0 else 0
        
        return {
            'total_ingredients': total_ingredients,
            'used_ingredients': used_ingredients,
            'efficiency_rate': efficiency,
            'usage_details': ingredient_usage
        }
    
    def get_expiry_analysis(self):
        """유통기한 분석"""
        ingredients = self.db_manager.get_ingredients()
        if not ingredients:
            return None
        
        today = datetime.now()
        expired = 0
        expiring_soon = 0  # 3일 이내
        fresh = 0
        
        for ing in ingredients:
            if ing.get('expiry_date'):
                try:
                    expiry = datetime.strptime(ing['expiry_date'], '%Y-%m-%d')
                    days_diff = (expiry - today).days
                    
                    if days_diff < 0:
                        expired += 1
                    elif days_diff <= 3:
                        expiring_soon += 1
                    else:
                        fresh += 1
                except:
                    continue
        
        return {
            'expired': expired,
            'expiring_soon': expiring_soon,
            'fresh': fresh,
            'total': expired + expiring_soon + fresh
        }

class MealPlanner:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_weekly_plan(self, start_date: date, preferences: str = ""):
        """주간 식단 계획 생성"""
        recipes = self.db_manager.get_recipes()
        if not recipes:
            return None
        
        # 7일간의 식단 계획
        meal_plan = {}
        meal_types = ['아침', '점심', '저녁']
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            meal_plan[date_str] = {}
            
            for meal_type in meal_types:
                # 간단한 로직으로 레시피 배정 (실제로는 더 복잡한 알고리즘 필요)
                if recipes:
                    selected_recipe = np.random.choice(recipes)
                    meal_plan[date_str][meal_type] = {
                        'recipe_id': selected_recipe['id'],
                        'recipe_title': selected_recipe['title'],
                        'difficulty': selected_recipe.get('difficulty_level', '보통'),
                        'cooking_time': selected_recipe.get('cooking_time', 30)
                    }
        
        return meal_plan
    
    def calculate_weekly_nutrition(self, meal_plan: Dict):
        """주간 영양 정보 계산 (예시)"""
        # 실제로는 영양 데이터베이스와 연동 필요
        nutrition_data = {
            'calories': np.random.randint(1800, 2200, 7),
            'protein': np.random.randint(60, 100, 7),
            'carbs': np.random.randint(200, 300, 7),
            'fat': np.random.randint(50, 80, 7)
        }
        
        return nutrition_data

class CostAnalyzer:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        # 재료별 평균 가격 (예시 데이터)
        self.ingredient_prices = {
            '양파': 2000, '마늘': 3000, '계란': 300, '쌀': 2500,
            '돼지고기': 15000, '닭가슴살': 8000, '두부': 2000,
            '간장': 3000, '고추장': 4000, '참기름': 8000,
            '당근': 1500, '감자': 2000, '대파': 1000
        }
    
    def calculate_recipe_cost(self, recipe_id: int):
        """레시피별 예상 비용 계산"""
        recipe = self.db_manager.get_recipe_with_ingredients(recipe_id)
        if not recipe or 'ingredients' not in recipe:
            return 0
        
        total_cost = 0
        for ing in recipe['ingredients']:
            ing_name = ing.get('ingredient_name', '')
            quantity = ing.get('quantity', 1)
            
            # 기본 가격에서 수량 비례 계산
            base_price = self.ingredient_prices.get(ing_name, 2000)  # 기본값 2000원
            ingredient_cost = base_price * quantity / 10  # 10분의 1 단위로 계산
            total_cost += ingredient_cost
        
        return int(total_cost)
    
    def get_cost_efficient_recipes(self, limit: int = 5):
        """가성비 좋은 레시피 랭킹"""
        recipes = self.db_manager.get_recipes()
        if not recipes:
            return []
        
        recipe_costs = []
        for recipe in recipes:
            cost = self.calculate_recipe_cost(recipe['id'])
            servings = recipe.get('servings', 1)
            cost_per_serving = cost / servings if servings > 0 else cost
            
            recipe_costs.append({
                'title': recipe['title'],
                'total_cost': cost,
                'cost_per_serving': cost_per_serving,
                'servings': servings,
                'usage_count': recipe.get('usage_count', 0)
            })
        
        # 1인분 비용 기준으로 정렬
        recipe_costs.sort(key=lambda x: x['cost_per_serving'])
        return recipe_costs[:limit]
    
    def get_category_spending(self):
        """카테고리별 지출 분석"""
        ingredients = self.db_manager.get_ingredients()
        if not ingredients:
            return None
        
        category_spending = {}
        for ing in ingredients:
            category = ing.get('category', '기타')
            quantity = ing.get('quantity', 1)
            price = self.ingredient_prices.get(ing['name'], 2000)
            cost = price * quantity / 10
            
            category_spending[category] = category_spending.get(category, 0) + cost
        
        return category_spending

def show_analytics_dashboard(db_manager):
    """통합 분석 대시보드"""
    analytics = FoodAnalytics(db_manager)
    
    # 탭으로 구분 (비용분석, 효율성분석 제거)
    tab1, tab2 = st.tabs([
        "📊 종합 통계", "🎯 효율성 분석"
    ])
    
    with tab1:
        show_comprehensive_stats(analytics, db_manager)
    
    with tab2:
        show_efficiency_analysis(analytics)

def show_comprehensive_stats(analytics, db_manager):
    """종합 통계 표시"""
    st.subheader("📊 실시간 대시보드")
    
    # 기본 지표
    ingredients = db_manager.get_ingredients()
    recipes = db_manager.get_recipes()
    shopping_items = db_manager.get_shopping_list()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 재료", len(ingredients))
    with col2:
        st.metric("총 레시피", len(recipes))
    with col3:
        st.metric("쇼핑 리스트", len(shopping_items))
    with col4:
        total_usage = sum(recipe.get('usage_count', 0) for recipe in recipes)
        st.metric("총 요리 횟수", total_usage)
    
    # 차트들
    col1, col2 = st.columns(2)
    
    with col1:
        # 재료 카테고리별 분포
        category_dist = analytics.get_ingredient_category_distribution()
        if category_dist:
            fig = px.pie(
                values=list(category_dist.values()),
                names=list(category_dist.keys()),
                title="재료 카테고리별 분포"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("재료 데이터가 없습니다.")
    
    with col2:
        # 레시피 난이도별 분포
        difficulty_stats = analytics.get_recipe_difficulty_stats()
        if difficulty_stats:
            fig = px.bar(
                x=list(difficulty_stats.keys()),
                y=list(difficulty_stats.values()),
                title="레시피 난이도별 분포"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("레시피 데이터가 없습니다.")
    


def show_meal_planning(meal_planner, db_manager):
    """식단 계획 표시"""
    st.subheader("📅 주간 식단 계획")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        start_date = st.date_input("시작 날짜", value=date.today())
        preferences = st.text_area("선호사항", placeholder="예: 저칼로리, 단백질 위주, 간단한 요리 등")
        
        if st.button("🍽️ 식단 계획 생성"):
            with st.spinner("AI가 식단을 계획하는 중..."):
                meal_plan = meal_planner.create_weekly_plan(start_date, preferences)
                
                if meal_plan:
                    st.session_state.current_meal_plan = meal_plan
                    st.success("식단 계획이 생성되었습니다!")
                else:
                    st.error("식단 계획 생성에 실패했습니다. 레시피를 먼저 등록해주세요.")
    
    with col2:
        st.subheader("🎯 목표 설정")
        target_calories = st.number_input("목표 칼로리 (일일)", min_value=1000, max_value=3000, value=2000)
        target_protein = st.number_input("목표 단백질 (g)", min_value=50, max_value=200, value=80)
        
        st.info(f"""
        **설정된 목표**
        - 칼로리: {target_calories} kcal/일
        - 단백질: {target_protein} g/일
        """)
    
    # 생성된 식단 계획 표시
    if hasattr(st.session_state, 'current_meal_plan') and st.session_state.current_meal_plan:
        st.subheader("📋 생성된 식단 계획")
        
        meal_plan = st.session_state.current_meal_plan
        
        for date_str, meals in meal_plan.items():
            with st.expander(f"📅 {date_str}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**🌅 아침**")
                    if '아침' in meals:
                        meal = meals['아침']
                        st.write(f"• {meal['recipe_title']}")
                        st.write(f"  난이도: {meal['difficulty']}")
                        st.write(f"  시간: {meal['cooking_time']}분")
                
                with col2:
                    st.write("**☀️ 점심**")
                    if '점심' in meals:
                        meal = meals['점심']
                        st.write(f"• {meal['recipe_title']}")
                        st.write(f"  난이도: {meal['difficulty']}")
                        st.write(f"  시간: {meal['cooking_time']}분")
                
                with col3:
                    st.write("**🌙 저녁**")
                    if '저녁' in meals:
                        meal = meals['저녁']
                        st.write(f"• {meal['recipe_title']}")
                        st.write(f"  난이도: {meal['difficulty']}")
                        st.write(f"  시간: {meal['cooking_time']}분")

def show_cost_analysis(cost_analyzer):
    """비용 분석 표시"""
    st.subheader("💰 비용 분석")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 가성비 좋은 레시피 TOP 5")
        cost_efficient = cost_analyzer.get_cost_efficient_recipes()
        
        if cost_efficient:
            for i, recipe in enumerate(cost_efficient, 1):
                with st.container():
                    st.write(f"**{i}. {recipe['title']}**")
                    st.write(f"   💰 총 비용: {recipe['total_cost']:,}원")
                    st.write(f"   👤 1인분: {recipe['cost_per_serving']:,.0f}원")
                    st.write(f"   🍽️ {recipe['servings']}인분")
                    st.write("---")
        else:
            st.info("레시피 데이터가 없습니다.")
    
    with col2:
        st.subheader("📊 카테고리별 지출")
        category_spending = cost_analyzer.get_category_spending()
        
        if category_spending:
            fig = px.bar(
                x=list(category_spending.keys()),
                y=list(category_spending.values()),
                title="카테고리별 예상 지출"
            )
            fig.update_yaxis(title="금액 (원)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("재료 데이터가 없습니다.")
    
    # 절약 팁
    st.subheader("💡 절약 팁")
    st.info("""
    **🎯 식비 절약 꿀팁**
    
    1. **계절 재료 활용**: 제철 재료는 가격이 저렴하고 영양가가 높습니다
    2. **대용량 구매**: 자주 사용하는 재료는 대용량으로 구매하여 단가를 낮추세요
    3. **냉동 보관**: 특가 재료를 구매해서 냉동 보관하여 활용하세요
    4. **잔여 재료 활용**: 남은 재료로 만들 수 있는 레시피를 우선 선택하세요
    5. **간단한 요리**: 복잡한 재료가 많이 들어가는 요리보다 간단한 요리를 선택하세요
    """)

def show_efficiency_analysis(analytics):
    """효율성 분석 표시"""
    st.subheader("🎯 효율성 분석")
    
    # 재료 활용 효율성
    efficiency_data = analytics.get_ingredient_usage_efficiency()
    if efficiency_data:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("총 재료 수", efficiency_data['total_ingredients'])
        with col2:
            st.metric("활용된 재료", efficiency_data['used_ingredients'])
        with col3:
            st.metric("활용률", f"{efficiency_data['efficiency_rate']:.1f}%")
        
        # 활용률 게이지 차트
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = efficiency_data['efficiency_rate'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "재료 활용률"},
            delta = {'reference': 80},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        st.plotly_chart(fig, use_container_width=True)
    
    # 유통기한 분석
    st.subheader("📅 유통기한 관리 현황")
    expiry_data = analytics.get_expiry_analysis()
    if expiry_data:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("신선한 재료", expiry_data['fresh'], delta_color="normal")
        with col2:
            st.metric("임박 재료", expiry_data['expiring_soon'], delta_color="inverse")
        with col3:
            st.metric("만료된 재료", expiry_data['expired'], delta_color="inverse")
        with col4:
            waste_rate = (expiry_data['expired'] / expiry_data['total'] * 100) if expiry_data['total'] > 0 else 0
            st.metric("낭비율", f"{waste_rate:.1f}%", delta_color="inverse")
        
        # 유통기한 상태 파이 차트
        if expiry_data['total'] > 0:
            fig = px.pie(
                values=[expiry_data['fresh'], expiry_data['expiring_soon'], expiry_data['expired']],
                names=['신선', '임박', '만료'],
                title="유통기한 상태 분포",
                color_discrete_map={'신선': 'green', '임박': 'orange', '만료': 'red'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # 개선 제안
    st.subheader("🚀 개선 제안")
    
    if efficiency_data and efficiency_data['efficiency_rate'] < 70:
        st.warning("**재료 활용률이 낮습니다!**")
        st.write("- 보유 재료를 활용한 레시피를 더 많이 시도해보세요")
        st.write("- 재료 구매 전 기존 재료 확인을 습관화하세요")
    
    if expiry_data and expiry_data['expired'] > 0:
        st.error("**만료된 재료가 있습니다!**")
        st.write("- 유통기한 임박 재료를 우선 사용하는 레시피를 추천받으세요")
        st.write("- 정기적인 냉장고 정리를 실시하세요")
    
    if expiry_data and expiry_data['expiring_soon'] > 0:
        st.warning("**유통기한 임박 재료가 있습니다!**")
        st.write("- 해당 재료를 활용한 레시피를 빠르게 만들어보세요")
        st.write("- 냉동 보관이 가능한 재료는 냉동실로 옮기세요")