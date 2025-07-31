import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from PIL import Image
import io

from database import SupabaseManager
from utils import ImageProcessor, OpenAIManager, format_recipe_for_display
from analytics import show_analytics_dashboard, MealPlanner

# 페이지 설정
st.set_page_config(
    page_title="스마트 냉장고 & 레시피 매니저",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화 (지연 로딩)
@st.cache_resource
def get_db_manager():
    return SupabaseManager()

@st.cache_resource
def get_image_processor():
    return ImageProcessor()

@st.cache_resource
def get_openai_manager():
    return OpenAIManager()

if 'db_manager' not in st.session_state:
    st.session_state.db_manager = get_db_manager()
if 'image_processor' not in st.session_state:
    st.session_state.image_processor = get_image_processor()
if 'openai_manager' not in st.session_state:
    st.session_state.openai_manager = get_openai_manager()

def main():
    st.title("🍽️ 오늘 뭐 먹지? 🥘")
    st.markdown("### 🥗 AI가 추천하는 맞춤형 레시피 🍳")
    st.markdown("---")
    
    # 탭 메뉴
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏠 홈", "📸 재료 등록", "🍽️ 레시피 추천", "📚 레시피 북", "🛒 쇼핑 리스트", "📅 식단 계획", "📊 통계 분석"
    ])
    
    with tab1:
        show_home_page()
    with tab2:
        show_ingredient_registration()
    with tab3:
        show_recipe_recommendation()
    with tab4:
        show_recipe_book()
    with tab5:
        show_shopping_list()
    with tab6:
        show_meal_planning()
    with tab7:
        show_statistics()

def show_home_page():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("🏠 홈 대시보드")
    with col2:
        if st.button("🔄 새로고침", key="home_refresh"):
            st.rerun()
    
    # 현재 냉장고 상태
    ingredients = st.session_state.db_manager.get_ingredients()
    recipes = st.session_state.db_manager.get_recipes()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("보유 재료", len(ingredients))
    
    with col2:
        st.metric("저장된 레시피", len(recipes))
    
    with col3:
        # 유통기한 임박 재료 계산
        expiring_soon = 0
        for ing in ingredients:
            if ing.get('expiry_date'):
                try:
                    expiry = datetime.strptime(ing['expiry_date'], '%Y-%m-%d')
                    if expiry <= datetime.now() + timedelta(days=3):
                        expiring_soon += 1
                except:
                    pass
        st.metric("유통기한 임박", expiring_soon, delta_color="inverse")
    
    with col4:
        shopping_items = st.session_state.db_manager.get_shopping_list()
        st.metric("쇼핑 리스트", len(shopping_items))
    
    st.markdown("---")
    
    # 최근 활동
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🥬 최근 등록된 재료")
        if ingredients:
            recent_ingredients = sorted(ingredients, key=lambda x: x.get('added_date', ''), reverse=True)[:5]
            for ing in recent_ingredients:
                st.write(f"• {ing['name']} ({ing.get('quantity', 0)} {ing.get('unit', '개')})")
        else:
            st.info("등록된 재료가 없습니다.")
    
    with col2:
        st.subheader("📖 인기 레시피")
        if recipes:
            popular_recipes = sorted(recipes, key=lambda x: x.get('usage_count', 0), reverse=True)[:5]
            for recipe in popular_recipes:
                st.write(f"• {recipe['title']} (사용: {recipe.get('usage_count', 0)}회)")
        else:
            st.info("저장된 레시피가 없습니다.")

def show_ingredient_registration():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("📸 재료 등록")
    with col2:
        if st.button("🔄 새로고침", key="ingredient_refresh"):
            st.rerun()
    
    tab1, tab2 = st.tabs(["📷 사진으로 등록", "✏️ 직접 입력"])
    
    with tab1:
        st.subheader("사진으로 재료 인식")
        
        uploaded_file = st.file_uploader(
            "냉장고 사진을 업로드하세요",
            type=['png', 'jpg', 'jpeg'],
            help="재료가 잘 보이는 사진을 업로드해주세요"
        )
        
        if uploaded_file is not None:
            # 이미지 표시
            image = Image.open(uploaded_file)
            st.image(image, caption="업로드된 이미지", use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🍎 스마트 재료 인식", use_container_width=True):
                    with st.spinner("AI가 이미지에서 재료를 직접 인식하는 중..."):
                        # 이미지 전처리
                        processed_image = st.session_state.image_processor.preprocess_image(image)
                        
                        # 직접 재료 식별
                        ingredients = st.session_state.image_processor.identify_ingredients_from_image(processed_image)
                        st.session_state.recognized_ingredients = ingredients
                        st.session_state.show_smart_result = True
            
            with col2:
                if st.button("📝 텍스트 추출", use_container_width=True):
                    with st.spinner("이미지에서 텍스트를 추출하는 중..."):
                        # 텍스트 추출
                        extracted_text = st.session_state.image_processor.extract_text_from_image(image)
                        st.session_state.extracted_text = extracted_text
                        st.session_state.show_text_result = True
            
            with col3:
                if st.button("🔄 초기화", use_container_width=True):
                    # 세션 상태 초기화
                    for key in ['recognized_ingredients', 'extracted_text', 'show_smart_result', 'show_text_result', 'show_analyzed_result']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            
            # 스마트 재료 인식 결과 표시
            if hasattr(st.session_state, 'show_smart_result') and st.session_state.show_smart_result:
                ingredients = st.session_state.recognized_ingredients
                
                if ingredients:
                    st.success(f"🎉 {len(ingredients)}개의 재료를 인식했습니다!")
                    
                    # 인식된 재료 확인 및 수정
                    st.subheader("🥬 인식된 재료 확인 및 수정")
                    
                    for i, ing in enumerate(ingredients):
                        confidence = ing.get('confidence', 0.8)
                        freshness = ing.get('freshness', '보통')
                        confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                        freshness_emoji = "✨" if freshness == "신선" else "⚠️" if freshness == "주의" else "📦"
                        
                        with st.expander(f"{confidence_color} {ing['name']} - {ing.get('quantity', 1)} {ing.get('unit', '개')} {freshness_emoji}"):
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                ing['name'] = st.text_input("재료명", ing['name'], key=f"smart_name_{i}")
                            with col2:
                                categories = ["채소", "육류", "유제품", "조미료", "곡물", "기타"]
                                current_category = ing.get('category', '기타')
                                try:
                                    category_index = categories.index(current_category)
                                except ValueError:
                                    category_index = 5  # 기타
                                ing['category'] = st.selectbox(
                                    "카테고리", 
                                    categories,
                                    index=category_index,
                                    key=f"smart_cat_{i}"
                                )
                            with col3:
                                ing['quantity'] = st.number_input("수량", value=float(ing.get('quantity', 1)), min_value=0.1, key=f"smart_qty_{i}")
                            with col4:
                                units = ["개", "kg", "g", "L", "ml", "팩", "봉"]
                                current_unit = ing.get('unit', '개')
                                try:
                                    unit_index = units.index(current_unit)
                                except ValueError:
                                    unit_index = 0  # 개
                                ing['unit'] = st.selectbox(
                                    "단위",
                                    units,
                                    index=unit_index,
                                    key=f"smart_unit_{i}"
                                )
                            
                            col5, col6 = st.columns(2)
                            with col5:
                                ing['expiry_date'] = st.date_input("유통기한", key=f"smart_exp_{i}")
                            with col6:
                                st.metric("신뢰도", f"{confidence:.1%}")
                    
                    if st.button("✅ 인식된 재료 모두 저장", type="primary"):
                        success_count = 0
                        for ing in ingredients:
                            if st.session_state.db_manager.add_ingredient(
                                name=ing['name'],
                                category=ing['category'],
                                quantity=ing['quantity'],
                                unit=ing['unit'],
                                expiry_date=str(ing.get('expiry_date', ''))
                            ):
                                success_count += 1
                        
                        st.success(f"🎉 {success_count}개의 재료가 저장되었습니다!")
                        # 세션 상태 초기화
                        for key in ['recognized_ingredients', 'show_smart_result']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                else:
                    st.warning("⚠️ 재료를 인식하지 못했습니다. 다른 각도에서 촬영하거나 텍스트 추출을 시도해보세요.")
            
            # 텍스트 추출 결과 표시
            if hasattr(st.session_state, 'show_text_result') and st.session_state.show_text_result:
                st.write("**📝 인식된 텍스트:**")
                st.code(st.session_state.extracted_text)
                
                if st.session_state.extracted_text:
                    if st.button("🤖 텍스트에서 재료 분석"):
                        with st.spinner("AI가 텍스트에서 재료를 분석하는 중..."):
                            ingredients = st.session_state.openai_manager.extract_ingredients_from_text(st.session_state.extracted_text)
                            st.session_state.analyzed_ingredients = ingredients
                            st.session_state.show_analyzed_result = True
                else:
                    st.info("💡 텍스트가 인식되지 않았습니다. 이미지가 선명한지 확인해주세요.")
            
            # 텍스트 분석 결과 표시
            if hasattr(st.session_state, 'show_analyzed_result') and st.session_state.show_analyzed_result:
                ingredients = st.session_state.analyzed_ingredients
                
                if ingredients:
                    st.success(f"📝 텍스트에서 {len(ingredients)}개의 재료를 분석했습니다!")
                    
                    # 분석된 재료 확인 및 수정
                    st.subheader("📝 분석된 재료 확인 및 수정")
                    
                    for i, ing in enumerate(ingredients):
                        with st.expander(f"📝 {ing['name']} - {ing.get('quantity', 1)} {ing.get('unit', '개')}"):
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                ing['name'] = st.text_input("재료명", ing['name'], key=f"text_name_{i}")
                            with col2:
                                categories = ["채소", "육류", "유제품", "조미료", "곡물", "기타"]
                                current_category = ing.get('category', '기타')
                                try:
                                    category_index = categories.index(current_category)
                                except ValueError:
                                    category_index = 5  # 기타
                                ing['category'] = st.selectbox(
                                    "카테고리", 
                                    categories,
                                    index=category_index,
                                    key=f"text_cat_{i}"
                                )
                            with col3:
                                ing['quantity'] = st.number_input("수량", value=float(ing.get('quantity', 1)), min_value=0.1, key=f"text_qty_{i}")
                            with col4:
                                units = ["개", "kg", "g", "L", "ml", "팩", "봉"]
                                current_unit = ing.get('unit', '개')
                                try:
                                    unit_index = units.index(current_unit)
                                except ValueError:
                                    unit_index = 0  # 개
                                ing['unit'] = st.selectbox(
                                    "단위",
                                    units,
                                    index=unit_index,
                                    key=f"text_unit_{i}"
                                )
                            
                            ing['expiry_date'] = st.date_input("유통기한", key=f"text_exp_{i}")
                    
                    if st.button("✅ 분석된 재료 모두 저장", type="primary"):
                        success_count = 0
                        for ing in ingredients:
                            if st.session_state.db_manager.add_ingredient(
                                name=ing['name'],
                                category=ing['category'],
                                quantity=ing['quantity'],
                                unit=ing['unit'],
                                expiry_date=str(ing.get('expiry_date', ''))
                            ):
                                success_count += 1
                        
                        st.success(f"🎉 {success_count}개의 재료가 저장되었습니다!")
                        # 세션 상태 초기화
                        for key in ['analyzed_ingredients', 'show_analyzed_result', 'extracted_text', 'show_text_result']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                else:
                    st.warning("⚠️ 텍스트에서 재료를 분석하지 못했습니다. 직접 입력을 시도해보세요.")
    
    with tab2:
        st.subheader("재료 직접 입력")
        
        with st.form("ingredient_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("재료명 *")
                category = st.selectbox("카테고리", ["채소", "육류", "유제품", "조미료", "곡물", "기타"])
                quantity = st.number_input("수량", min_value=0.0, value=1.0, step=0.1)
            
            with col2:
                unit = st.selectbox("단위", ["개", "kg", "g", "L", "ml", "팩", "봉"])
                expiry_date = st.date_input("유통기한")
            
            submitted = st.form_submit_button("재료 추가")
            
            if submitted and name:
                if st.session_state.db_manager.add_ingredient(
                    name=name,
                    category=category,
                    quantity=quantity,
                    unit=unit,
                    expiry_date=str(expiry_date)
                ):
                    st.success(f"{name}이(가) 추가되었습니다!")
                    st.rerun()
                else:
                    st.error("재료 추가에 실패했습니다.")
    
    # 현재 보유 재료 목록
    st.markdown("---")
    st.subheader("🥬 현재 보유 재료")
    
    ingredients = st.session_state.db_manager.get_ingredients()
    if ingredients:
        df = pd.DataFrame(ingredients)
        st.dataframe(df[['name', 'category', 'quantity', 'unit', 'expiry_date']], use_container_width=True)
    else:
        st.info("등록된 재료가 없습니다.")

def show_recipe_recommendation():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("🍽️ 레시피 추천")
    with col2:
        if st.button("🔄 새로고침", key="recipe_refresh"):
            st.rerun()
    
    ingredients = st.session_state.db_manager.get_ingredients()
    
    if not ingredients:
        st.warning("먼저 재료를 등록해주세요!")
        return
    
    # 메뉴룰렛과 일반 추천 탭 분리
    tab1, tab2 = st.tabs(["🎯 메뉴룰렛", "🤖 AI 맞춤 추천"])
    
    with tab1:
        show_menu_roulette(ingredients)
    
    with tab2:
        show_ai_recipe_recommendation(ingredients)
    
def show_menu_roulette(ingredients):
    st.subheader("🎯 오늘 뭐 먹지? 메뉴룰렛!")
    st.markdown("고민 그만! 룰렛이 대신 골라드려요 🎲")
    
    # 룰렛 카테고리 선택
    col1, col2 = st.columns(2)
    
    with col1:
        roulette_type = st.selectbox(
            "룰렛 종류 선택",
            ["나라별 메뉴", "재료별 메뉴", "상황별 메뉴", "랜덤 메뉴"]
        )
    
    with col2:
        difficulty_pref = st.selectbox(
            "난이도 선호",
            ["상관없음", "간단한 요리", "보통", "도전적인 요리"]
        )
    
    # 룰렛 메뉴 데이터
    menu_categories = {
        "나라별 메뉴": [
            "한국", "중국", "일본", "이탈리아", "프랑스", "미국", "태국", "인도",
            "멕시코", "베트남", "스페인", "그리스", "터키", "브라질"
        ],
        "재료별 메뉴": [
            "닭고기 요리", "돼지고기 요리", "소고기 요리", "해산물 요리", "채소 요리",
            "계란 요리", "면 요리", "밥 요리", "국물 요리", "볶음 요리"
        ],
        "상황별 메뉴": [
            "혼밥 메뉴", "술안주", "다이어트", "든든한 한끼", "간단 간식",
            "손님 접대", "아이 반찬", "도시락", "야식", "브런치"
        ],
        "랜덤 메뉴": [
            "김치찌개", "된장찌개", "불고기", "비빔밥", "볶음밥", "라면",
            "파스타", "피자", "샐러드", "스테이크", "카레", "짜장면",
            "치킨", "햄버거", "초밥", "우동", "떡볶이", "순대국"
        ]
    }
    
    selected_menus = menu_categories[roulette_type]
    
    # 룰렛 실행
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🎲 룰렛 돌리기!", type="primary", use_container_width=True):
            import random
            import time
            
            # 룰렛 애니메이션 효과
            placeholder = st.empty()
            
            for i in range(10):
                random_choice = random.choice(selected_menus)
                placeholder.markdown(f"### 🎯 {random_choice}")
                time.sleep(0.2)
            
            # 최종 선택
            final_choice = random.choice(selected_menus)
            placeholder.markdown(f"### 🎉 오늘의 메뉴: **{final_choice}** 🎉")
            
            st.session_state.roulette_result = final_choice
            st.balloons()
    
    # 룰렛 결과가 있으면 레시피 추천
    if hasattr(st.session_state, 'roulette_result'):
        st.markdown("---")
        st.subheader(f"🍽️ {st.session_state.roulette_result} 레시피 추천")
        
        # 보유 재료 기반 추천
        ingredient_names = [ing['name'] for ing in ingredients]
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🤖 AI 레시피 생성", use_container_width=True):
                with st.spinner(f"{st.session_state.roulette_result} 레시피를 생성하는 중..."):
                    # 룰렛 결과와 보유 재료를 조합한 프롬프트
                    roulette_prompt = f"{st.session_state.roulette_result} 요리를 만들고 싶습니다. "
                    if difficulty_pref != "상관없음":
                        roulette_prompt += f"난이도는 {difficulty_pref}으로 해주세요. "
                    
                    recipe = st.session_state.openai_manager.generate_recipe(
                        ingredient_names[:10],  # 너무 많은 재료는 제한
                        roulette_prompt
                    )
                    
                    if recipe:
                        st.session_state.roulette_recipe = recipe
                        st.rerun()
        
        with col2:
            if st.button("🔄 다시 돌리기", use_container_width=True):
                if 'roulette_result' in st.session_state:
                    del st.session_state.roulette_result
                if 'roulette_recipe' in st.session_state:
                    del st.session_state.roulette_recipe
                st.rerun()
        
        # 생성된 레시피 표시
        if hasattr(st.session_state, 'roulette_recipe'):
            recipe = st.session_state.roulette_recipe
            st.markdown(format_recipe_for_display(recipe))
            
            # 레시피 저장 및 쇼핑 리스트 추가 버튼
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 레시피 저장", key="save_roulette_recipe"):
                    save_recipe_to_db(recipe)
            
            with col2:
                if st.button("🛒 부족한 재료 쇼핑리스트 추가", key="add_roulette_shopping"):
                    add_missing_ingredients_to_shopping(recipe, ingredient_names)

def show_ai_recipe_recommendation(ingredients):
    # 사용할 재료 선택
    st.subheader("🤖 AI 맞춤 레시피 추천")
    ingredient_names = [ing['name'] for ing in ingredients]
    selected_ingredients = st.multiselect(
        "레시피에 사용할 재료를 선택하세요",
        ingredient_names,
        default=ingredient_names[:5] if len(ingredient_names) >= 5 else ingredient_names
    )
    
    # 선호사항 입력
    preferences = st.text_area(
        "선호사항 (선택사항)",
        placeholder="예: 매운 음식 좋아함, 간단한 요리, 30분 이내 조리 등"
    )
    
    if st.button("🍳 레시피 추천받기") and selected_ingredients:
        with st.spinner("맞춤 레시피를 생성하는 중..."):
            recipe = st.session_state.openai_manager.generate_recipe(
                selected_ingredients, 
                preferences
            )
            
            if recipe:
                # 레시피 표시
                st.markdown(format_recipe_for_display(recipe))
                
                # 레시피 저장 옵션
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("💾 레시피 저장"):
                        save_recipe_to_db(recipe)
                
                with col2:
                    # 부족한 재료 확인
                    recipe_ingredient_names = [ing.get('name') for ing in recipe.get('ingredients', [])]
                    missing_analysis = st.session_state.openai_manager.suggest_missing_ingredients(
                        recipe_ingredient_names, 
                        selected_ingredients
                    )
                    
                    # missing_analysis가 딕셔너리인지 확인
                    if isinstance(missing_analysis, dict):
                        essential_missing = missing_analysis.get('essential', [])
                        optional_missing = missing_analysis.get('optional', [])
                        substitutes = missing_analysis.get('substitutes', [])
                        
                        if essential_missing:
                            st.warning("**부족한 필수 재료:**")
                            for item in essential_missing:
                                st.write(f"• {item}")
                            
                            if st.button("🛒 쇼핑 리스트에 추가"):
                                with st.spinner("쇼핑 리스트에 추가하는 중..."):
                                    try:
                                        success_count = 0
                                        failed_items = []
                                        
                                        st.write("디버그: 추가할 재료들")
                                        st.write(essential_missing)
                                        
                                        for item in essential_missing:
                                            st.write(f"추가 시도: {item}")
                                            if st.session_state.db_manager.add_to_shopping_list(item, 1, "개"):
                                                success_count += 1
                                                st.write(f"✅ {item} 추가 성공")
                                            else:
                                                failed_items.append(item)
                                                st.write(f"❌ {item} 추가 실패")
                                        
                                        if success_count > 0:
                                            st.success(f"✅ {success_count}개 재료가 쇼핑 리스트에 추가되었습니다!")
                                            if failed_items:
                                                st.warning(f"⚠️ {len(failed_items)}개 재료 추가 실패: {', '.join(failed_items)}")
                                            st.rerun()
                                        else:
                                            st.error("❌ 모든 재료 추가에 실패했습니다. 콘솔 로그를 확인해주세요.")
                                            
                                    except Exception as e:
                                        st.error(f"❌ 쇼핑 리스트 추가 중 오류 발생: {str(e)}")
                                        st.write("오류 상세:", e)
                        
                        if optional_missing:
                            st.info("**선택적 재료:**")
                            for item in optional_missing:
                                st.write(f"• {item}")
                        
                        if substitutes:
                            st.info("**대체 가능한 재료:**")
                            for sub in substitutes:
                                if isinstance(sub, dict):
                                    st.write(f"• {sub.get('original', '')} → {sub.get('substitute', '')}")
                                    if sub.get('note'):
                                        st.caption(f"  💡 {sub.get('note')}")
                        
                        if not essential_missing and not optional_missing:
                            st.success("✅ 모든 재료가 준비되어 있습니다!")
                    else:
                        # missing_analysis가 리스트인 경우 (fallback)
                        if missing_analysis:
                            st.warning("**부족한 재료:**")
                            for item in missing_analysis:
                                st.write(f"• {item}")
                            
                            if st.button("🛒 쇼핑 리스트에 추가"):
                                for item in missing_analysis:
                                    st.session_state.db_manager.add_to_shopping_list(item, 1, "개")
                                st.success("쇼핑 리스트에 추가되었습니다!")
                        else:
                            st.success("✅ 모든 재료가 준비되어 있습니다!")
            else:
                st.error("레시피 생성에 실패했습니다. 다시 시도해주세요.")

def save_recipe_to_db(recipe):
    """레시피를 데이터베이스에 저장하는 함수"""
    with st.spinner("레시피를 저장하는 중..."):
        try:
            # 재료 정보 변환
            recipe_ingredients = []
            for ing in recipe.get('ingredients', []):
                ingredient_data = {
                    'name': ing.get('name', ''),
                    'quantity': float(ing.get('quantity', 1)),
                    'unit': ing.get('unit', '개'),
                    'is_essential': ing.get('is_essential', True)
                }
                recipe_ingredients.append(ingredient_data)
            
            success = st.session_state.db_manager.add_recipe(
                title=recipe.get('title', '제목 없음'),
                description=recipe.get('description', ''),
                instructions='\n'.join(recipe.get('instructions', [])),
                ingredients=recipe_ingredients,
                cooking_time=recipe.get('cooking_time'),
                servings=recipe.get('servings'),
                difficulty=recipe.get('difficulty', '보통')
            )
            
            if success:
                st.success("✅ 레시피가 성공적으로 저장되었습니다!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ 레시피 저장에 실패했습니다.")
                
        except Exception as e:
            st.error(f"❌ 레시피 저장 중 오류 발생: {str(e)}")

def add_missing_ingredients_to_shopping(recipe, available_ingredients):
    """부족한 재료를 쇼핑리스트에 추가하는 함수"""
    with st.spinner("부족한 재료를 확인하는 중..."):
        try:
            recipe_ingredient_names = [ing.get('name') for ing in recipe.get('ingredients', [])]
            missing_analysis = st.session_state.openai_manager.suggest_missing_ingredients(
                recipe_ingredient_names, 
                available_ingredients
            )
            
            if isinstance(missing_analysis, dict):
                essential_missing = missing_analysis.get('essential', [])
                
                if essential_missing:
                    success_count = 0
                    for item in essential_missing:
                        if st.session_state.db_manager.add_to_shopping_list(item, 1, "개"):
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"✅ {success_count}개 재료가 쇼핑 리스트에 추가되었습니다!")
                        st.rerun()
                    else:
                        st.error("❌ 쇼핑 리스트 추가에 실패했습니다.")
                else:
                    st.success("✅ 모든 재료가 준비되어 있습니다!")
            else:
                if missing_analysis:
                    success_count = 0
                    for item in missing_analysis:
                        if st.session_state.db_manager.add_to_shopping_list(item, 1, "개"):
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"✅ {success_count}개 재료가 쇼핑 리스트에 추가되었습니다!")
                        st.rerun()
                else:
                    st.success("✅ 모든 재료가 준비되어 있습니다!")
                    
        except Exception as e:
            st.error(f"❌ 쇼핑 리스트 추가 중 오류 발생: {str(e)}")

def show_recipe_book():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("📚 레시피 북")
    with col2:
        if st.button("🔄 새로고침", key="recipe_book_refresh"):
            st.rerun()
    
    recipes = st.session_state.db_manager.get_recipes()
    
    if not recipes:
        st.info("저장된 레시피가 없습니다.")
        return
    
    # 검색 및 필터
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("🔍 레시피 검색", placeholder="레시피 제목으로 검색...")
    with col2:
        difficulty_filter = st.selectbox("난이도 필터", ["전체", "쉬움", "보통", "어려움"])
    
    # 필터링
    filtered_recipes = recipes
    if search_term:
        filtered_recipes = [r for r in filtered_recipes if search_term.lower() in r['title'].lower()]
    if difficulty_filter != "전체":
        filtered_recipes = [r for r in filtered_recipes if r.get('difficulty_level') == difficulty_filter]
    
    # 레시피 목록 표시
    for recipe in filtered_recipes:
        with st.expander(f"🍽️ {recipe['title']} ({recipe.get('difficulty_level', '보통')})"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**설명:** {recipe.get('description', '설명 없음')}")
                st.write(f"**조리시간:** {recipe.get('cooking_time', '미정')}분")
                st.write(f"**인분:** {recipe.get('servings', '미정')}인분")
                st.write(f"**사용횟수:** {recipe.get('usage_count', 0)}회")
                
                # 상세 레시피 보기
                if st.button(f"상세 보기", key=f"detail_{recipe['id']}"):
                    detailed_recipe = st.session_state.db_manager.get_recipe_with_ingredients(recipe['id'])
                    if detailed_recipe:
                        st.markdown("**재료:**")
                        for ing in detailed_recipe.get('ingredients', []):
                            essential = "✅" if ing.get('is_essential') else "⭕"
                            st.write(f"- {essential} {ing.get('ingredient_name')} {ing.get('quantity')} {ing.get('unit')}")
                        
                        st.markdown("**조리법:**")
                        instructions = detailed_recipe.get('instructions', '').split('\n')
                        for i, step in enumerate(instructions, 1):
                            if step.strip():
                                st.write(f"{i}. {step}")
            
            with col2:
                if st.button(f"🍳 요리 완료", key=f"cook_{recipe['id']}"):
                    rating = st.slider("평점", 1, 5, 3, key=f"rating_{recipe['id']}")
                    notes = st.text_area("메모", key=f"notes_{recipe['id']}")
                    
                    if st.session_state.db_manager.add_cooking_history(recipe['id'], rating, notes):
                        st.success("요리 기록이 저장되었습니다!")
                        st.rerun()

def show_shopping_list():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("🛒 쇼핑 리스트")
    with col2:
        if st.button("🔄 새로고침", key="shopping_refresh"):
            st.rerun()
    
    shopping_items = st.session_state.db_manager.get_shopping_list()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("구매할 재료")
        
        if shopping_items:
            for item in shopping_items:
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    st.write(f"• {item['ingredient_name']} ({item['quantity']} {item['unit']})")
                with col_b:
                    if st.button("✅", key=f"buy_{item['id']}", help="구매 완료"):
                        # 구매 완료 처리 - 실제 데이터베이스 업데이트
                        try:
                            result = st.session_state.db_manager.supabase.table("shopping_list").update(
                                {"is_purchased": True}
                            ).eq("id", item['id']).execute()
                            st.success("구매 완료!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"구매 완료 처리 실패: {e}")
                with col_c:
                    if st.button("❌", key=f"del_{item['id']}", help="삭제"):
                        # 삭제 처리 - 실제 데이터베이스에서 삭제
                        try:
                            result = st.session_state.db_manager.supabase.table("shopping_list").delete().eq("id", item['id']).execute()
                            st.success("삭제됨!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"삭제 실패: {e}")
        else:
            st.info("쇼핑 리스트가 비어있습니다.")
    
    with col2:
        st.subheader("재료 추가")
        
        with st.form("add_shopping_item"):
            ingredient_name = st.text_input("재료명")
            quantity = st.number_input("수량", min_value=0.1, value=1.0)
            unit = st.selectbox("단위", ["개", "kg", "g", "L", "ml", "팩", "봉"])
            
            if st.form_submit_button("추가"):
                if ingredient_name:
                    if st.session_state.db_manager.add_to_shopping_list(ingredient_name, quantity, unit):
                        st.success("쇼핑 리스트에 추가되었습니다!")
                        st.rerun()
                    else:
                        st.error("쇼핑 리스트 추가에 실패했습니다.")

def show_meal_planning():
    """식단 계획 페이지"""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("📅 식단 계획")
    with col2:
        if st.button("🔄 새로고침", key="meal_planning_refresh"):
            st.rerun()
    
    # MealPlanner 인스턴스 생성
    meal_planner = MealPlanner(st.session_state.db_manager)
    
    st.subheader("🍽️ 주간 식단 계획 생성")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 식단 계획 설정
        start_date = st.date_input("📅 시작 날짜", value=datetime.now().date())
        
        col_a, col_b = st.columns(2)
        with col_a:
            meal_types = st.multiselect(
                "🍽️ 식사 유형 선택",
                ["아침", "점심", "저녁", "간식"],
                default=["점심", "저녁"]
            )
        with col_b:
            target_calories = st.number_input("🎯 목표 칼로리 (일일)", min_value=1000, max_value=3000, value=2000)
        
        preferences = st.text_area(
            "🎨 선호사항 및 요구사항",
            placeholder="예: 저칼로리, 단백질 위주, 간단한 요리, 매운 음식 선호, 30분 이내 조리 등",
            height=100
        )
        
        # 식단 계획 생성 버튼들
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🤖 AI 자동 추천", type="primary", use_container_width=True):
                with st.spinner("AI가 맞춤형 식단을 계획하는 중..."):
                    # AI 기반 식단 계획 생성
                    ai_meal_plan = generate_ai_meal_plan(
                        st.session_state.db_manager,
                        start_date,
                        meal_types,
                        preferences,
                        target_calories
                    )
                    
                    if ai_meal_plan:
                        st.session_state.current_meal_plan = ai_meal_plan
                        st.session_state.meal_plan_type = "AI 추천"
                        st.success("🎉 AI 맞춤형 식단 계획이 생성되었습니다!")
                        st.rerun()
                    else:
                        st.error("❌ AI 식단 계획 생성에 실패했습니다. 레시피를 먼저 등록해주세요.")
        
        with col_btn2:
            if st.button("🎲 랜덤 생성", use_container_width=True):
                with st.spinner("랜덤 식단을 생성하는 중..."):
                    # 기본 랜덤 식단 계획 생성
                    random_meal_plan = meal_planner.create_weekly_plan(start_date, preferences)
                    
                    if random_meal_plan:
                        st.session_state.current_meal_plan = random_meal_plan
                        st.session_state.meal_plan_type = "랜덤 생성"
                        st.success("🎲 랜덤 식단 계획이 생성되었습니다!")
                        st.rerun()
                    else:
                        st.error("❌ 식단 계획 생성에 실패했습니다. 레시피를 먼저 등록해주세요.")
    
    with col2:
        st.subheader("📊 영양 목표")
        
        # 영양 목표 설정
        target_protein = st.number_input("단백질 (g)", min_value=50, max_value=200, value=80)
        target_carbs = st.number_input("탄수화물 (g)", min_value=100, max_value=400, value=250)
        target_fat = st.number_input("지방 (g)", min_value=30, max_value=150, value=60)
        
        st.info(f"""
        **📋 설정된 목표**
        - 🔥 칼로리: {target_calories} kcal/일
        - 🥩 단백질: {target_protein} g/일
        - 🍞 탄수화물: {target_carbs} g/일
        - 🥑 지방: {target_fat} g/일
        """)
    
    # 생성된 식단 계획 표시
    if hasattr(st.session_state, 'current_meal_plan') and st.session_state.current_meal_plan:
        st.markdown("---")
        
        plan_type = getattr(st.session_state, 'meal_plan_type', '생성된')
        st.subheader(f"📋 {plan_type} 식단 계획")
        
        meal_plan = st.session_state.current_meal_plan
        
        # 주간 식단을 일별로 표시
        for date_str, meals in meal_plan.items():
            with st.expander(f"📅 {date_str}"):
                if meals:
                    cols = st.columns(len(meals))
                    
                    for i, (meal_type, meal_info) in enumerate(meals.items()):
                        with cols[i]:
                            # 식사 시간별 이모지
                            meal_emoji = {
                                '아침': '🌅',
                                '점심': '☀️', 
                                '저녁': '🌙',
                                '간식': '🍪'
                            }.get(meal_type, '🍽️')
                            
                            st.write(f"**{meal_emoji} {meal_type}**")
                            st.write(f"🍽️ {meal_info['recipe_title']}")
                            st.write(f"⏱️ {meal_info['cooking_time']}분")
                            st.write(f"📊 {meal_info['difficulty']}")
                else:
                    st.info("이 날은 계획된 식사가 없습니다.")
        
        # 식단 계획 관리 버튼들
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🛒 필요한 재료 쇼핑리스트 추가"):
                with st.spinner("필요한 재료를 분석하는 중..."):
                    # 식단에 필요한 모든 재료 수집
                    needed_ingredients = set()
                    for meals in meal_plan.values():
                        for meal_info in meals.values():
                            recipe_detail = st.session_state.db_manager.get_recipe_with_ingredients(meal_info['recipe_id'])
                            if recipe_detail and 'ingredients' in recipe_detail:
                                for ing in recipe_detail['ingredients']:
                                    needed_ingredients.add(ing.get('ingredient_name', ''))
                    
                    # 보유 재료와 비교하여 부족한 재료만 쇼핑리스트에 추가
                    available_ingredients = {ing['name'] for ing in st.session_state.db_manager.get_ingredients()}
                    missing_ingredients = needed_ingredients - available_ingredients
                    
                    success_count = 0
                    for ingredient in missing_ingredients:
                        if st.session_state.db_manager.add_to_shopping_list(ingredient, 1, "개"):
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"🛒 {success_count}개의 재료가 쇼핑 리스트에 추가되었습니다!")
                    else:
                        st.info("추가할 재료가 없거나 이미 모든 재료를 보유하고 있습니다.")
        
        with col2:
            if st.button("💾 식단 계획 저장"):
                st.success("식단 계획이 저장되었습니다!")
        
        with col3:
            if st.button("🔄 식단 계획 초기화"):
                if hasattr(st.session_state, 'current_meal_plan'):
                    del st.session_state.current_meal_plan
                if hasattr(st.session_state, 'meal_plan_type'):
                    del st.session_state.meal_plan_type
                st.rerun()

def generate_ai_meal_plan(db_manager, start_date, meal_types, preferences, target_calories):
    """AI 기반 맞춤형 식단 계획 생성"""
    try:
        # 사용 가능한 재료와 레시피 가져오기
        ingredients = db_manager.get_ingredients()
        recipes = db_manager.get_recipes()
        
        print(f"디버그: 레시피 개수 = {len(recipes)}")
        print(f"디버그: 레시피 목록 = {[r['title'] for r in recipes]}")
        
        if not recipes:
            print("디버그: 레시피가 없어서 None 반환")
            return None
        
        # 선호사항을 고려한 레시피 필터링
        filtered_recipes = recipes
        if preferences:
            # 간단한 키워드 매칭
            if "간단" in preferences or "쉬움" in preferences:
                temp_filtered = [r for r in recipes if r.get('difficulty_level') == '쉬움']
                if temp_filtered:
                    filtered_recipes = temp_filtered
            elif "어려움" in preferences or "복잡" in preferences:
                temp_filtered = [r for r in recipes if r.get('difficulty_level') == '어려움']
                if temp_filtered:
                    filtered_recipes = temp_filtered
        
        print(f"디버그: 필터링된 레시피 개수 = {len(filtered_recipes)}")
        
        # 7일간의 식단 계획 생성
        meal_plan = {}
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            meal_plan[date_str] = {}
            
            for meal_type in meal_types:
                if filtered_recipes:
                    # numpy 대신 random 사용
                    import random
                    selected_recipe = random.choice(filtered_recipes)
                    meal_plan[date_str][meal_type] = {
                        'recipe_id': selected_recipe['id'],
                        'recipe_title': selected_recipe['title'],
                        'difficulty': selected_recipe.get('difficulty_level', '보통'),
                        'cooking_time': selected_recipe.get('cooking_time', 30)
                    }
        
        print(f"디버그: 생성된 식단 계획 = {meal_plan}")
        return meal_plan
        
    except Exception as e:
        print(f"AI 식단 계획 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def show_statistics():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("📊 통계 분석")
    with col2:
        if st.button("🔄 새로고침", key="statistics_refresh"):
            st.rerun()
    
    # 새로운 analytics 모듈 사용
    show_analytics_dashboard(st.session_state.db_manager)

if __name__ == "__main__":
    main()