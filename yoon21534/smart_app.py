import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from database import SmartFridgeDB
from ai_services import SmartFridgeAI
from config import SUPABASE_URL, SUPABASE_KEY, TEST_MODE
import os
from PIL import Image
import io

# 페이지 설정
st.set_page_config(
    page_title="🤖 AI 스마트 냉장고",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'AI 대시보드'

# 데이터베이스 및 AI 서비스 연결
@st.cache_resource
def get_services():
    try:
        db = SmartFridgeDB()
        ai = SmartFridgeAI()
        
        # 데이터베이스 연결 상태 확인
        if hasattr(db, 'test_mode') and db.test_mode:
            st.info("🧪 테스트 모드로 실행 중입니다. (메모리 저장)")
        else:
            st.success("✅ Supabase 데이터베이스에 연결되었습니다.")
        
        return db, ai
    except Exception as e:
        st.error(f"서비스 연결 오류: {e}")
        return None, None

db, ai = get_services()

# 사이드바 - 사용자 인증 (기존과 동일)
def sidebar_auth():
    st.sidebar.title("🔐 로그인")
    
    if TEST_MODE:
        st.sidebar.info("🧪 테스트 모드로 실행 중입니다.")
    
    if st.session_state.user_id is None:
        # 빠른 로그인 버튼들
        st.sidebar.write("🚀 **빠른 로그인:**")
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("테스트 계정 1", type="primary"):
                if db:
                    try:
                        # 먼저 기존 사용자 확인
                        user_id = db.get_user_id("demo@smartfridge.com")
                        if not user_id:
                            # 사용자가 없으면 새로 생성
                            user_id = db.create_user("demo@smartfridge.com", "테스트 사용자 1")
                        
                        if user_id:
                            st.session_state.user_id = user_id
                            st.session_state.user_email = "demo@smartfridge.com"
                            st.success("테스트 계정 1로 로그인 성공!")
                            st.rerun()
                        else:
                            st.error("테스트 계정 1 생성에 실패했습니다.")
                    except Exception as e:
                        st.error(f"로그인 중 오류가 발생했습니다: {str(e)}")
                else:
                    st.error("데이터베이스 연결에 실패했습니다.")
        
        with col2:
            if st.button("테스트 계정 2", type="secondary"):
                if db:
                    try:
                        # 먼저 기존 사용자 확인
                        user_id = db.get_user_id("test@smartfridge.com")
                        if not user_id:
                            # 사용자가 없으면 새로 생성
                            user_id = db.create_user("test@smartfridge.com", "테스트 사용자 2")
                        
                        if user_id:
                            st.session_state.user_id = user_id
                            st.session_state.user_email = "test@smartfridge.com"
                            st.success("테스트 계정 2로 로그인 성공!")
                            st.rerun()
                        else:
                            st.error("테스트 계정 2 생성에 실패했습니다.")
                    except Exception as e:
                        st.error(f"로그인 중 오류가 발생했습니다: {str(e)}")
                else:
                    st.error("데이터베이스 연결에 실패했습니다.")
        
        # 일반 로그인/회원가입
        st.sidebar.write("---")
        st.sidebar.write("🔑 **일반 로그인:**")
        
        email = st.sidebar.text_input("이메일", placeholder="user@example.com")
        name = st.sidebar.text_input("이름", placeholder="사용자명")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("로그인"):
                if not email or not name:
                    st.error("이메일과 이름을 입력해주세요.")
                elif not db:
                    st.error("데이터베이스 연결에 실패했습니다.")
                else:
                    try:
                        user_id = db.get_user_id(email)
                        if user_id:
                            st.session_state.user_id = user_id
                            st.session_state.user_email = email
                            st.success("로그인 성공!")
                            st.rerun()
                        else:
                            st.error("사용자를 찾을 수 없습니다. 회원가입을 해주세요.")
                    except Exception as e:
                        st.error(f"로그인 중 오류가 발생했습니다: {str(e)}")
        
        with col2:
            if st.button("회원가입"):
                if not email or not name:
                    st.error("이메일과 이름을 입력해주세요.")
                elif not db:
                    st.error("데이터베이스 연결에 실패했습니다.")
                else:
                    try:
                        # 기존 사용자 확인
                        existing_user = db.get_user_id(email)
                        if existing_user:
                            st.warning("이미 존재하는 이메일입니다. 로그인을 해주세요.")
                        else:
                            user_id = db.create_user(email, name)
                            if user_id:
                                st.session_state.user_id = user_id
                                st.session_state.user_email = email
                                st.success("회원가입 성공!")
                                st.rerun()
                            else:
                                st.error("회원가입에 실패했습니다.")
                    except Exception as e:
                        st.error(f"회원가입 중 오류가 발생했습니다: {str(e)}")
    else:
        st.sidebar.success(f"안녕하세요, {st.session_state.user_email}님!")
        
        with st.sidebar.expander("👤 내 정보"):
            st.write(f"**이메일:** {st.session_state.user_email}")
            st.write(f"**사용자 ID:** {st.session_state.user_id[:8]}...")
        
        if st.sidebar.button("로그아웃"):
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.rerun()

# AI 대시보드
def ai_dashboard():
    st.title("🤖 AI 스마트 냉장고")
    
    if not db or not ai:
        st.error("서비스 연결에 실패했습니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다. 사이드바에서 로그인해주세요.")
        return
    
    # AI 기능 소개
    st.markdown("""
    ### 🌟 AI 기능들
    - 🍳 **AI 레시피 추천**: 보유 재료로 만들 수 있는 맞춤 레시피
    - 📅 **스마트 식단 계획**: 영양 균형을 고려한 자동 식단 생성
    - 📸 **재료 인식**: 사진으로 재료 자동 등록
    - 🥗 **영양 분석**: 식단의 영양소 분석 및 건강 조언
    - 👨‍🍳 **요리 도우미**: 실시간 요리 가이드
    """)
    
    # 통계 정보
    stats = db.get_ingredient_statistics(st.session_state.user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 식재료", stats["total"])
    with col2:
        st.metric("유통기한 임박", stats["expiring_soon"], delta=f"-{stats['expiring_soon']}")
    with col3:
        st.metric("만료된 재료", stats["expired"], delta=f"-{stats['expired']}")
    with col4:
        st.metric("AI 추천 가능", "✅" if stats["total"] > 0 else "❌")
    
    # 빠른 AI 기능 버튼들
    st.markdown("### 🚀 빠른 AI 기능")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🍳 AI 레시피 추천", use_container_width=True):
            st.session_state.current_page = "AI 레시피 추천"
            st.rerun()
    
    with col2:
        if st.button("📅 스마트 식단 계획", use_container_width=True):
            st.session_state.current_page = "스마트 식단 계획"
            st.rerun()
    
    with col3:
        if st.button("📸 재료 인식", use_container_width=True):
            st.session_state.current_page = "재료 인식"
            st.rerun()

# AI 레시피 추천 페이지
def ai_recipe_recommendation():
    st.header("🍳 AI 레시피 추천")
    
    if not db or not ai:
        st.error("서비스 연결에 실패했습니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다.")
        return
    
    # 보유 재료 확인
    ingredients = db.get_ingredients(st.session_state.user_id)
    
    if not ingredients:
        st.warning("등록된 재료가 없습니다. 먼저 재료를 등록해주세요.")
        return
    
    st.subheader("🥬 현재 보유 재료")
    
    # 재료 선택
    selected_ingredients = []
    cols = st.columns(3)
    
    for i, ingredient in enumerate(ingredients):
        with cols[i % 3]:
            if st.checkbox(f"{ingredient['name']} ({ingredient['quantity']}{ingredient['unit']})", 
                          key=f"ing_{ingredient['id']}"):
                selected_ingredients.append(ingredient)
    
    if not selected_ingredients:
        st.info("레시피 추천을 위해 사용할 재료를 선택해주세요.")
        return
    
    # 식단 선호도 입력
    st.subheader("🎯 선호도 설정")
    dietary_preferences = st.text_input(
        "식단 선호도 (선택사항)", 
        placeholder="예: 매운 음식 선호, 저염식, 다이어트 중"
    )
    
    # AI 레시피 추천 실행
    if st.button("🤖 AI 레시피 추천 받기", type="primary"):
        with st.spinner("AI가 맞춤 레시피를 추천하고 있습니다..."):
            try:
                recommended_recipes = ai.recommend_recipes(selected_ingredients, dietary_preferences)
                
                if recommended_recipes:
                    st.success(f"🎉 {len(recommended_recipes)}개의 레시피를 추천드립니다!")
                    
                    for i, recipe in enumerate(recommended_recipes):
                        with st.expander(f"🍽️ {recipe['name']} ({recipe['category']})"):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write(f"**설명:** {recipe['description']}")
                                st.write(f"**필요 재료:** {recipe['ingredients']}")
                                st.write("**조리 방법:**")
                                st.write(recipe['instructions'])
                                
                            with col2:
                                st.metric("조리시간", f"{recipe['cooking_time']}분")
                                st.metric("난이도", recipe['difficulty'])
                                if 'nutrition_info' in recipe:
                                    st.write(f"**영양정보:** {recipe['nutrition_info']}")
                            
                            # 레시피 저장 버튼
                            if st.button(f"📖 레시피 저장", key=f"save_{i}"):
                                success = db.add_recipe(
                                    st.session_state.user_id,
                                    recipe['name'],
                                    recipe['description'],
                                    recipe['ingredients'],
                                    recipe['cooking_time'],
                                    recipe['difficulty'],
                                    recipe['category'],
                                    ""
                                )
                                if success:
                                    st.success("레시피가 저장되었습니다!")
                                else:
                                    st.error("레시피 저장에 실패했습니다.")
                else:
                    st.error("레시피 추천에 실패했습니다. 다시 시도해주세요.")
                    
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")

# 스마트 식단 계획 페이지
def smart_meal_planning():
    st.header("📅 스마트 식단 계획")
    
    if not db or not ai:
        st.error("서비스 연결에 실패했습니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        days = st.selectbox("계획 기간", [3, 5, 7, 14], index=2)
        dietary_goals = st.text_area(
            "식단 목표", 
            placeholder="예: 체중 감량, 근육 증가, 건강한 식단, 당뇨 관리 등"
        )
    
    with col2:
        # 보유 재료 표시
        ingredients = db.get_ingredients(st.session_state.user_id)
        st.write("**현재 보유 재료:**")
        if ingredients:
            for ing in ingredients[:5]:  # 최대 5개만 표시
                st.write(f"• {ing['name']} ({ing['quantity']}{ing['unit']})")
            if len(ingredients) > 5:
                st.write(f"• ... 외 {len(ingredients)-5}개")
        else:
            st.write("등록된 재료가 없습니다.")
    
    if st.button("🤖 AI 식단 계획 생성", type="primary"):
        if not dietary_goals:
            st.warning("식단 목표를 입력해주세요.")
            return
            
        with st.spinner(f"AI가 {days}일간의 맞춤 식단을 계획하고 있습니다..."):
            try:
                meal_plan = ai.create_meal_plan(days, dietary_goals, ingredients)
                
                if meal_plan and 'meal_plan' in meal_plan:
                    st.success(f"🎉 {days}일간의 식단 계획이 완성되었습니다!")
                    
                    # 식단 계획 표시
                    for day_key, day_plan in meal_plan['meal_plan'].items():
                        day_num = day_key.split('_')[1]
                        st.subheader(f"📅 {day_num}일차")
                        
                        cols = st.columns(4)
                        meals = ['breakfast', 'lunch', 'dinner', 'snack']
                        meal_names = ['🌅 아침', '☀️ 점심', '🌙 저녁', '🍪 간식']
                        
                        for i, (meal_key, meal_name) in enumerate(zip(meals, meal_names)):
                            if meal_key in day_plan:
                                with cols[i]:
                                    meal_info = day_plan[meal_key]
                                    st.write(f"**{meal_name}**")
                                    st.write(meal_info['name'])
                                    st.write(f"🔥 {meal_info['calories']}kcal")
                                    if 'nutrients' in meal_info:
                                        st.write(f"🥗 {meal_info['nutrients']}")
                    
                    # 쇼핑 리스트
                    if 'shopping_list' in meal_plan and meal_plan['shopping_list']:
                        st.subheader("🛒 쇼핑 리스트")
                        for item in meal_plan['shopping_list']:
                            st.write(f"• {item}")
                    
                    # 영양 분석
                    if 'nutrition_summary' in meal_plan:
                        st.subheader("🥗 영양 분석")
                        st.info(meal_plan['nutrition_summary'])
                        
                else:
                    st.error("식단 계획 생성에 실패했습니다. 다시 시도해주세요.")
                    
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")

# 재료 인식 페이지
def ingredient_recognition():
    st.header("📸 재료 인식")
    
    if not db or not ai:
        st.error("서비스 연결에 실패했습니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다.")
        return
    
    st.markdown("""
    ### 📱 사진으로 재료 등록하기
    재료 사진을 업로드하면 AI가 자동으로 인식하여 냉장고에 등록해드립니다.
    """)
    
    # 이미지 업로드
    uploaded_file = st.file_uploader(
        "재료 사진 업로드", 
        type=['png', 'jpg', 'jpeg'],
        help="재료가 잘 보이는 사진을 업로드해주세요."
    )
    
    if uploaded_file is not None:
        # 이미지 표시
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드된 이미지", use_column_width=True)
        
        if st.button("🤖 AI로 재료 인식하기", type="primary"):
            with st.spinner("AI가 이미지를 분석하고 있습니다..."):
                try:
                    # 이미지를 바이트로 변환
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='JPEG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    # AI 인식 실행
                    result = ai.recognize_ingredient_from_image(img_byte_arr)
                    
                    if result and result['ingredients']:
                        st.success(f"🎉 {len(result['ingredients'])}개의 재료를 인식했습니다!")
                        st.info(f"인식 신뢰도: {result['confidence']}/10")
                        
                        # 인식된 재료들 표시 및 등록
                        for i, ingredient in enumerate(result['ingredients']):
                            with st.expander(f"🥬 {ingredient['name']} (신선도: {ingredient['freshness']}/10)"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # 사용자가 수정 가능한 입력 필드
                                    name = st.text_input("재료명", value=ingredient['name'], key=f"name_{i}")
                                    quantity = st.number_input("수량", value=float(ingredient['quantity']), key=f"qty_{i}")
                                    unit = st.selectbox("단위", ["개", "kg", "g", "L", "ml", "봉", "팩"], 
                                                      index=0 if ingredient['unit'] not in ["개", "kg", "g", "L", "ml", "봉", "팩"] else ["개", "kg", "g", "L", "ml", "봉", "팩"].index(ingredient['unit']), 
                                                      key=f"unit_{i}")
                                
                                with col2:
                                    category = st.selectbox("카테고리", ["채소", "과일", "육류", "수산물", "유제품", "조미료", "기타"],
                                                          index=0 if ingredient['category'] not in ["채소", "과일", "육류", "수산물", "유제품", "조미료", "기타"] else ["채소", "과일", "육류", "수산물", "유제품", "조미료", "기타"].index(ingredient['category']),
                                                          key=f"cat_{i}")
                                    expiry_date = st.date_input("유통기한", 
                                                              value=date.today() + timedelta(days=ingredient['estimated_expiry_days']),
                                                              key=f"exp_{i}")
                                    location = st.selectbox("보관 위치", ["냉장고", "냉동고", "실온", "기타"], key=f"loc_{i}")
                                
                                # 재료 등록 버튼
                                if st.button(f"📦 {name} 등록하기", key=f"add_{i}"):
                                    success = db.add_ingredient(
                                        st.session_state.user_id, name, quantity, unit,
                                        date.today(), expiry_date, category, location
                                    )
                                    if success:
                                        st.success(f"{name}이(가) 성공적으로 등록되었습니다!")
                                    else:
                                        st.error("재료 등록에 실패했습니다.")
                    else:
                        st.warning("재료를 인식하지 못했습니다. 다른 사진을 시도해보세요.")
                        
                except Exception as e:
                    st.error(f"이미지 인식 중 오류가 발생했습니다: {str(e)}")

# 영양 분석 페이지
def nutrition_analysis():
    st.header("🥗 영양 분석")
    
    if not db or not ai:
        st.error("서비스 연결에 실패했습니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다.")
        return
    
    # 최근 식단 계획 가져오기
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    meal_plans = db.get_meal_plans(st.session_state.user_id, start_date, end_date)
    
    if not meal_plans:
        st.warning("분석할 식단 계획이 없습니다. 먼저 식단을 계획해주세요.")
        return
    
    st.subheader("📊 최근 7일간 식단 분석")
    
    if st.button("🤖 AI 영양 분석 시작", type="primary"):
        with st.spinner("AI가 영양을 분석하고 있습니다..."):
            try:
                analysis = ai.analyze_nutrition(meal_plans)
                
                if analysis:
                    # 건강 점수
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("건강 점수", f"{analysis.get('health_score', 0)}/10")
                    with col2:
                        st.metric("총 칼로리", f"{analysis.get('total_calories', 0)}kcal")
                    with col3:
                        st.metric("분석 완료", "✅")
                    
                    # 영양소 비율
                    if 'macronutrients' in analysis:
                        st.subheader("🍎 영양소 비율")
                        macros = analysis['macronutrients']
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.info(f"**탄수화물**\n{macros.get('carbs', 'N/A')}")
                        with col2:
                            st.info(f"**단백질**\n{macros.get('protein', 'N/A')}")
                        with col3:
                            st.info(f"**지방**\n{macros.get('fat', 'N/A')}")
                    
                    # 부족한 영양소
                    if 'vitamins_minerals' in analysis and analysis['vitamins_minerals']:
                        st.subheader("⚠️ 부족한 영양소")
                        for nutrient in analysis['vitamins_minerals']:
                            st.warning(f"• {nutrient}")
                    
                    # 개선 방안
                    if 'recommendations' in analysis and analysis['recommendations']:
                        st.subheader("💡 개선 방안")
                        for rec in analysis['recommendations']:
                            st.success(f"• {rec}")
                    
                    # 주의사항
                    if 'warnings' in analysis and analysis['warnings']:
                        st.subheader("🚨 주의사항")
                        for warning in analysis['warnings']:
                            st.error(f"• {warning}")
                            
                else:
                    st.error("영양 분석에 실패했습니다. 다시 시도해주세요.")
                    
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")

# 메인 앱
def main():
    sidebar_auth()
    
    if st.session_state.user_id is None:
        ai_dashboard()
    else:
        # 로그인된 사용자 메뉴
        st.sidebar.success(f"안녕하세요, {st.session_state.user_email}님!")
        
        if st.sidebar.button("로그아웃"):
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.rerun()
        
        st.sidebar.write("---")
        st.sidebar.header("🤖 AI 메뉴")
        
        # AI 메뉴 버튼들
        if st.sidebar.button("🏠 AI 대시보드", use_container_width=True):
            st.session_state.current_page = "AI 대시보드"
            st.rerun()
        
        if st.sidebar.button("🍳 AI 레시피 추천", use_container_width=True):
            st.session_state.current_page = "AI 레시피 추천"
            st.rerun()
        
        if st.sidebar.button("📅 스마트 식단 계획", use_container_width=True):
            st.session_state.current_page = "스마트 식단 계획"
            st.rerun()
        
        if st.sidebar.button("📸 재료 인식", use_container_width=True):
            st.session_state.current_page = "재료 인식"
            st.rerun()
        
        if st.sidebar.button("🥗 영양 분석", use_container_width=True):
            st.session_state.current_page = "영양 분석"
            st.rerun()
        
        st.sidebar.write("---")
        st.sidebar.header("📋 기본 메뉴")
        
        if st.sidebar.button("🥬 식재료 관리", use_container_width=True):
            st.session_state.current_page = "식재료 관리"
            st.rerun()
        
        if st.sidebar.button("📖 레시피 관리", use_container_width=True):
            st.session_state.current_page = "레시피 관리"
            st.rerun()
        
        # 현재 페이지 실행
        current_page = st.session_state.get('current_page', 'AI 대시보드')
        
        if current_page == "AI 대시보드":
            ai_dashboard()
        elif current_page == "AI 레시피 추천":
            ai_recipe_recommendation()
        elif current_page == "스마트 식단 계획":
            smart_meal_planning()
        elif current_page == "재료 인식":
            ingredient_recognition()
        elif current_page == "영양 분석":
            nutrition_analysis()
        elif current_page == "식재료 관리":
            # 기존 기능 import 필요
            from app import ingredients_page
            ingredients_page()
        elif current_page == "레시피 관리":
            from app import recipes_page
            recipes_page()

if __name__ == "__main__":
    main()