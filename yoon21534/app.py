import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from database import SmartFridgeDB
from config import SUPABASE_URL, SUPABASE_KEY, TEST_MODE
import os

# 페이지 설정
st.set_page_config(
    page_title="스마트 냉장고",
    page_icon="🥘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = '대시보드'

# 데이터베이스 연결
@st.cache_resource
def get_db():
    try:
        return SmartFridgeDB()
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {e}")
        st.info("테스트 모드로 실행됩니다.")
        return None

db = get_db()

# 사이드바 - 사용자 인증
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
                    # 테스트 계정 1로 로그인
                    user_id = db.get_user_id("demo@smartfridge.com")
                    if not user_id:
                        # 테스트 계정이 없으면 생성
                        user_id = db.create_user("demo@smartfridge.com", "테스트 사용자 1")
                    
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.user_email = "demo@smartfridge.com"
                        st.success("테스트 계정 1로 로그인 성공!")
                        st.rerun()
                    else:
                        st.error("테스트 계정 1 로그인에 실패했습니다.")
                else:
                    st.error("데이터베이스 연결에 실패했습니다.")
        
        with col2:
            if st.button("테스트 계정 2", type="secondary"):
                if db:
                    # 테스트 계정 2로 로그인
                    user_id = db.get_user_id("test@smartfridge.com")
                    if not user_id:
                        # 테스트 계정이 없으면 생성
                        user_id = db.create_user("test@smartfridge.com", "테스트 사용자 2")
                    
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.user_email = "test@smartfridge.com"
                        st.success("테스트 계정 2로 로그인 성공!")
                        st.rerun()
                    else:
                        st.error("테스트 계정 2 로그인에 실패했습니다.")
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
                if email and name and db:
                    user_id = db.get_user_id(email)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.user_email = email
                        st.success("로그인 성공!")
                        st.rerun()
                    else:
                        st.error("사용자를 찾을 수 없습니다.")
                else:
                    st.error("이메일과 이름을 입력해주세요.")
        
        with col2:
            if st.button("회원가입"):
                if email and name and db:
                    user_id = db.create_user(email, name)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.user_email = email
                        st.success("회원가입 성공!")
                        st.rerun()
                    else:
                        st.error("회원가입에 실패했습니다.")
                else:
                    st.error("이메일과 이름을 입력해주세요.")
    else:
        st.sidebar.success(f"안녕하세요, {st.session_state.user_email}님!")
        
        # 현재 사용자 정보 표시
        with st.sidebar.expander("👤 내 정보"):
            st.write(f"**이메일:** {st.session_state.user_email}")
            st.write(f"**사용자 ID:** {st.session_state.user_id[:8]}...")
        
        if st.sidebar.button("로그아웃"):
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.rerun()

# 메인 대시보드
def main_dashboard():
    st.title("🥘 스마트 냉장고")
    
    if not db:
        st.error("데이터베이스 연결에 실패했습니다. 테스트 모드로 실행됩니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다. 사이드바에서 로그인해주세요.")
        
        # 데모 정보 표시
        st.info("💡 **팁:** 사이드바의 '데모 계정' 버튼을 클릭하면 바로 사용할 수 있습니다!")
        return
    
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
        st.metric("카테고리 수", len(stats["categories"]))
    
    # 유통기한 임박 알림
    expiring_ingredients = db.get_expiring_ingredients(st.session_state.user_id, 3)
    if expiring_ingredients:
        st.warning(f"⚠️ {len(expiring_ingredients)}개의 식재료가 곧 유통기한이 만료됩니다!")
        
        for ingredient in expiring_ingredients:
            days_left = (datetime.strptime(ingredient["expiry_date"], "%Y-%m-%d").date() - date.today()).days
            st.info(f"📅 {ingredient['name']} - {ingredient['expiry_date']} (D-{days_left})")

# 식재료 관리 페이지
def ingredients_page():
    st.header("🥬 식재료 관리")
    
    if not db:
        st.error("데이터베이스 연결에 실패했습니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다.")
        return
    
    tab1, tab2 = st.tabs(["재료 추가", "재료 목록"])
    
    with tab1:
        st.subheader("새 재료 추가")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("재료명", placeholder="양파")
            quantity = st.number_input("수량", min_value=0.0, value=1.0, step=0.1)
            unit = st.selectbox("단위", ["개", "kg", "g", "L", "ml", "봉", "팩"])
            category = st.selectbox("카테고리", ["채소", "과일", "육류", "수산물", "유제품", "조미료", "기타"])
        
        with col2:
            purchase_date = st.date_input("구매일", value=date.today())
            expiry_date = st.date_input("유통기한", value=date.today() + timedelta(days=7))
            location = st.selectbox("보관 위치", ["냉장고", "냉동고", "실온", "기타"])
        
        if st.button("재료 추가", type="primary"):
            if name and quantity > 0:
                success = db.add_ingredient(
                    st.session_state.user_id, name, quantity, unit,
                    purchase_date, expiry_date, category, location
                )
                if success:
                    st.success("재료가 성공적으로 추가되었습니다!")
                    st.rerun()
                else:
                    st.error("재료 추가에 실패했습니다.")
            else:
                st.error("필수 정보를 입력해주세요.")
    
    with tab2:
        st.subheader("재료 목록")
        
        ingredients = db.get_ingredients(st.session_state.user_id)
        if ingredients:
            # DataFrame으로 변환
            df = pd.DataFrame(ingredients)
            df['expiry_date'] = pd.to_datetime(df['expiry_date'])
            df['days_left'] = (df['expiry_date'].dt.date - date.today()).dt.days
            
            # 유통기한 임박 표시
            def highlight_expiring(row):
                if row['days_left'] <= 3:
                    return ['background-color: #ffcccc'] * len(row)
                elif row['days_left'] <= 7:
                    return ['background-color: #ffffcc'] * len(row)
                return [''] * len(row)
            
            # 표시할 컬럼 선택
            display_df = df[['name', 'quantity', 'unit', 'category', 'location', 'expiry_date', 'days_left']].copy()
            display_df['days_left'] = display_df['days_left'].apply(lambda x: f"D-{x}" if x >= 0 else f"만료 {abs(x)}일")
            
            st.dataframe(
                display_df.style.apply(highlight_expiring, axis=1),
                use_container_width=True
            )
            
            # 삭제 기능
            st.subheader("재료 삭제")
            ingredient_names = [f"{ing['name']} ({ing['quantity']}{ing['unit']})" for ing in ingredients]
            selected_ingredient = st.selectbox("삭제할 재료 선택", ingredient_names)
            
            if st.button("삭제", type="secondary"):
                selected_index = ingredient_names.index(selected_ingredient)
                ingredient_id = ingredients[selected_index]['id']
                if db.delete_ingredient(ingredient_id):
                    st.success("재료가 삭제되었습니다!")
                    st.rerun()
                else:
                    st.error("삭제에 실패했습니다.")
        else:
            st.info("등록된 재료가 없습니다.")

# 레시피 관리 페이지
def recipes_page():
    st.header("📖 레시피 관리")
    
    if not db:
        st.error("데이터베이스 연결에 실패했습니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다.")
        return
    
    tab1, tab2 = st.tabs(["레시피 추가", "레시피 목록"])
    
    with tab1:
        st.subheader("새 레시피 추가")
        
        name = st.text_input("레시피명", placeholder="김치찌개")
        description = st.text_area("설명", placeholder="맛있는 김치찌개 만드는 방법")
        
        col1, col2 = st.columns(2)
        with col1:
            cooking_time = st.number_input("조리시간 (분)", min_value=1, value=30)
            difficulty = st.selectbox("난이도", ["초급", "중급", "고급"])
        
        with col2:
            category = st.selectbox("카테고리", ["한식", "양식", "중식", "일식", "간식", "기타"])
            image_url = st.text_input("이미지 URL (선택사항)", placeholder="https://...")
        
        ingredients_list = st.text_area("필요한 재료", placeholder="김치 200g, 돼지고기 100g, 두부 1/2모...")
        
        if st.button("레시피 추가", type="primary"):
            if name:
                success = db.add_recipe(
                    st.session_state.user_id, name, description,
                    ingredients_list, cooking_time, difficulty, category, image_url
                )
                if success:
                    st.success("레시피가 성공적으로 추가되었습니다!")
                    st.rerun()
                else:
                    st.error("레시피 추가에 실패했습니다.")
            else:
                st.error("레시피명을 입력해주세요.")
    
    with tab2:
        st.subheader("레시피 목록")
        
        recipes = db.get_recipes(st.session_state.user_id)
        if recipes:
            for recipe in recipes:
                with st.expander(f"📖 {recipe['name']} ({recipe['category']})"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        if recipe['description']:
                            st.write(f"**설명:** {recipe['description']}")
                        if recipe['ingredients_list']:
                            st.write(f"**재료:** {recipe['ingredients_list']}")
                        st.write(f"**조리시간:** {recipe['cooking_time']}분")
                        st.write(f"**난이도:** {recipe['difficulty']}")
                    
                    with col2:
                        if recipe['image_url']:
                            st.image(recipe['image_url'], width=150)
        else:
            st.info("등록된 레시피가 없습니다.")

# 식단 계획 페이지
def meal_plan_page():
    st.header("📅 식단 계획")
    
    if not db:
        st.error("데이터베이스 연결에 실패했습니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다.")
        return
    
    tab1, tab2 = st.tabs(["식단 추가", "식단 보기"])
    
    with tab1:
        st.subheader("새 식단 계획 추가")
        
        col1, col2 = st.columns(2)
        with col1:
            plan_date = st.date_input("날짜", value=date.today())
            meal_type = st.selectbox("식사 유형", ["아침", "점심", "저녁", "간식"])
        
        with col2:
            recipes = db.get_recipes(st.session_state.user_id)
            recipe_options = {f"{r['name']} ({r['category']})": r['id'] for r in recipes}
            selected_recipe = st.selectbox("레시피 선택", list(recipe_options.keys()))
            recipe_id = recipe_options[selected_recipe] if selected_recipe else None
        
        notes = st.text_area("메모", placeholder="특별한 요청사항이나 메모")
        
        if st.button("식단 추가", type="primary"):
            if recipe_id:
                success = db.add_meal_plan(
                    st.session_state.user_id, recipe_id, plan_date, meal_type, notes
                )
                if success:
                    st.success("식단이 성공적으로 추가되었습니다!")
                    st.rerun()
                else:
                    st.error("식단 추가에 실패했습니다.")
            else:
                st.error("레시피를 선택해주세요.")
    
    with tab2:
        st.subheader("식단 보기")
        
        # 날짜 범위 선택
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일", value=date.today())
        with col2:
            end_date = st.date_input("종료일", value=date.today() + timedelta(days=6))
        
        meal_plans = db.get_meal_plans(st.session_state.user_id, start_date, end_date)
        
        if meal_plans:
            # 날짜별로 그룹화
            plans_by_date = {}
            for plan in meal_plans:
                plan_date = plan['plan_date']
                if plan_date not in plans_by_date:
                    plans_by_date[plan_date] = []
                plans_by_date[plan_date].append(plan)
            
            # 날짜별로 표시
            for plan_date in sorted(plans_by_date.keys()):
                st.subheader(f"📅 {plan_date}")
                for plan in plans_by_date[plan_date]:
                    recipe_name = plan['recipes']['name'] if plan['recipes'] else "레시피 없음"
                    st.write(f"🍽️ **{plan['meal_type']}:** {recipe_name}")
                    if plan['notes']:
                        st.write(f"📝 {plan['notes']}")
        else:
            st.info("선택한 기간에 등록된 식단이 없습니다.")

# 통계 페이지
def statistics_page():
    st.header("📊 통계")
    
    if not db:
        st.error("데이터베이스 연결에 실패했습니다.")
        return
    
    if st.session_state.user_id is None:
        st.warning("로그인이 필요합니다.")
        return
    
    stats = db.get_ingredient_statistics(st.session_state.user_id)
    ingredients = db.get_ingredients(st.session_state.user_id)
    
    if ingredients:
        # 카테고리별 분포 차트
        if stats["categories"]:
            fig_category = px.pie(
                values=list(stats["categories"].values()),
                names=list(stats["categories"].keys()),
                title="카테고리별 재료 분포"
            )
            st.plotly_chart(fig_category, use_container_width=True)
        
        # 유통기한 현황
        df = pd.DataFrame(ingredients)
        df['expiry_date'] = pd.to_datetime(df['expiry_date'])
        df['days_left'] = (df['expiry_date'].dt.date - date.today()).dt.days
        
        # 유통기한 임박 현황
        expiring_soon = df[df['days_left'] <= 7]
        if not expiring_soon.empty:
            fig_expiring = px.bar(
                expiring_soon,
                x='name',
                y='days_left',
                title="유통기한 임박 재료 (7일 이내)",
                color='days_left',
                color_continuous_scale='RdYlGn_r'
            )
            st.plotly_chart(fig_expiring, use_container_width=True)
    else:
        st.info("등록된 재료가 없습니다.")

# 메인 앱
def main():
    sidebar_auth()
    
    if st.session_state.user_id is None:
        main_dashboard()
    else:
        # 로그인된 사용자 정보 표시
        st.sidebar.success(f"안녕하세요, {st.session_state.user_email}님!")
        
        # 로그아웃 버튼
        if st.sidebar.button("로그아웃"):
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.rerun()
        
        st.sidebar.write("---")
        
        # 메뉴 - 모두 펼쳐진 상태
        st.sidebar.header("📋 메뉴")
        
        if st.sidebar.button("🏠 대시보드", use_container_width=True):
            st.session_state.current_page = "대시보드"
            st.rerun()
        
        if st.sidebar.button("🥬 식재료 관리", use_container_width=True):
            st.session_state.current_page = "식재료 관리"
            st.rerun()
        
        if st.sidebar.button("📖 레시피 관리", use_container_width=True):
            st.session_state.current_page = "레시피 관리"
            st.rerun()
        
        if st.sidebar.button("📅 식단 계획", use_container_width=True):
            st.session_state.current_page = "식단 계획"
            st.rerun()
        
        if st.sidebar.button("📊 통계", use_container_width=True):
            st.session_state.current_page = "통계"
            st.rerun()
        
        # 현재 페이지에 따라 해당 함수 실행
        current_page = st.session_state.get('current_page', '대시보드')
        
        if current_page == "대시보드":
            main_dashboard()
        elif current_page == "식재료 관리":
            ingredients_page()
        elif current_page == "레시피 관리":
            recipes_page()
        elif current_page == "식단 계획":
            meal_plan_page()
        elif current_page == "통계":
            statistics_page()

if __name__ == "__main__":
    main() 