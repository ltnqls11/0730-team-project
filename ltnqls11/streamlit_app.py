import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import openai
from dotenv import load_dotenv
import os

# .env 파일에서 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="🍳 GPT가 추천하는 우리집 스마트 냉장고",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 환경 변수 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    OPENAI_MODEL = "gpt-4o-mini"

# 데이터베이스 연결 함수
@st.cache_resource
def get_db_connection():
    """데이터베이스 연결 객체를 반환합니다."""
    try:
        conn = sqlite3.connect('ltnqls11/recipe_management.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {e}")
        return None

# 인증 관련 함수들 제거됨 - 누구나 접근 가능

# 재료 관리 함수들 (모든 사용자 공용)
def get_all_ingredients():
    """모든 보유 재료 목록을 조회합니다."""
    conn = get_db_connection()
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor()
        sql = """
            SELECT ui.user_ingredient_id, ui.quantity, ui.purchase_date, ui.expiration_date, ui.location,
                   i.ingredient_name, i.category, i.unit
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            ORDER BY ui.expiration_date ASC
        """
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        st.error(f"재료 조회 오류: {e}")
        return []
    finally:
        conn.close()

def add_ingredient(ingredient_name, quantity, purchase_date, expiration_date, location):
    """보유 재료를 추가합니다."""
    conn = get_db_connection()
    if conn is None:
        return False, "데이터베이스 연결에 실패했습니다."
    
    try:
        cursor = conn.cursor()
        # 재료 ID 찾기 또는 새로 추가
        cursor.execute("SELECT ingredient_id FROM Ingredients WHERE ingredient_name = ?", (ingredient_name,))
        ingredient_result = cursor.fetchone()
        
        if ingredient_result:
            ingredient_id = ingredient_result['ingredient_id']
        else:
            cursor.execute("INSERT INTO Ingredients (ingredient_name) VALUES (?)", (ingredient_name,))
            ingredient_id = cursor.lastrowid
            conn.commit()
        
        # User_Ingredients 테이블에 추가 (user_id는 1로 고정)
        cursor.execute(
            "INSERT INTO User_Ingredients (user_id, ingredient_id, quantity, purchase_date, expiration_date, location) VALUES (?, ?, ?, ?, ?, ?)",
            (1, ingredient_id, quantity, purchase_date, expiration_date, location)
        )
        conn.commit()
        return True, "재료가 성공적으로 추가되었습니다!"
    except Exception as e:
        return False, f"재료 추가 오류: {e}"
    finally:
        conn.close()

def delete_ingredient(user_ingredient_id):
    """보유 재료를 삭제합니다."""
    conn = get_db_connection()
    if conn is None:
        return False, "데이터베이스 연결에 실패했습니다."
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM User_Ingredients WHERE user_ingredient_id = ?", (user_ingredient_id,))
        conn.commit()
        return True, "재료가 성공적으로 삭제되었습니다!"
    except Exception as e:
        return False, f"재료 삭제 오류: {e}"
    finally:
        conn.close()

# GPT 레시피 추천 함수
def recommend_recipes(allergies=None, preferences=None):
    """GPT를 사용하여 레시피를 추천합니다."""
    if not OPENAI_API_KEY:
        return "OpenAI API 키가 설정되지 않았습니다."
    
    # 모든 재료 조회
    ingredients = get_all_ingredients()
    if not ingredients:
        return "보유 재료가 없으면 레시피 추천이 어렵습니다. 재료를 먼저 추가해주세요."
    
    # 재료 정보 정리
    ingredient_details = []
    for ing in ingredients:
        try:
            exp_date = datetime.strptime(ing['expiration_date'], '%Y-%m-%d')
            days_left = (exp_date - datetime.now()).days
            urgency = "🔴 곧 만료" if days_left <= 2 else "🟡 주의" if days_left <= 5 else "🟢 신선함"
        except ValueError:
            urgency = "⚪ 날짜 오류"
        ingredient_details.append(f"{ing['ingredient_name']} ({ing['quantity']}{ing['unit'] or '개'}, {urgency})")
    
    # GPT 프롬프트 생성
    system_prompt = """당신은 미슐랭 스타 셰프이자 영양 전문가입니다. 
    냉장고 재료를 최대한 활용하여 맛있고 영양가 있는 레시피를 추천해주세요.
    
    응답 형식:
    🍳 **레시피 제목**
    ⏰ 조리시간: X분
    👥 인분: X인분
    🌟 난이도: 쉬움/보통/어려움
    
    📋 **주재료 (보유중)**
    - 재료명: 사용량
    
    🛒 **추가 필요 재료** (선택사항)
    - 재료명: 사용량
    
    👨‍🍳 **조리법**
    1. 단계별 상세 설명
    
    💡 **셰프의 팁**
    - 맛을 더하는 비법이나 변형 방법
    
    한국인의 입맛에 맞는 현실적이고 실용적인 레시피를 제공해주세요."""
    
    user_prompt = f"""
    🥘 **현재 보유 재료:**
    {chr(10).join(ingredient_details)}
    
    🚫 **알레르기:** {', '.join(allergies) if allergies else '없음'}
    ❤️ **선호사항:** {', '.join(preferences) if preferences else '없음'}
    
    위 재료들을 최대한 활용하여 3가지 다양한 요리를 추천해주세요. 
    만료 임박 재료(🔴, 🟡)를 우선적으로 사용하는 레시피를 포함해주세요.
    """
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1200,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"레시피 추천 오류: {e}"

# 대시보드 통계 함수
def get_dashboard_stats():
    """대시보드용 통계 데이터를 조회합니다."""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor()
        
        # 재료 수
        cursor.execute("SELECT COUNT(*) as count FROM User_Ingredients")
        ingredient_count = cursor.fetchone()['count']
        
        # 카테고리별 재료 분포
        cursor.execute("""
            SELECT COALESCE(i.category, '기타') as category, COUNT(*) as count
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            GROUP BY COALESCE(i.category, '기타')
        """)
        category_distribution = [dict(row) for row in cursor.fetchall()]
        
        # 유통기한 현황
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN DATE(expiration_date) <= DATE('now') THEN '만료됨'
                    WHEN DATE(expiration_date) <= DATE('now', '+3 days') THEN '곧 만료'
                    WHEN DATE(expiration_date) <= DATE('now', '+7 days') THEN '주의'
                    ELSE '신선함'
                END as status,
                COUNT(*) as count
            FROM User_Ingredients 
            GROUP BY status
        """)
        expiration_status = [dict(row) for row in cursor.fetchall()]
        
        # 위치별 재료 분포
        cursor.execute("""
            SELECT COALESCE(location, '미지정') as location, COUNT(*) as count
            FROM User_Ingredients 
            GROUP BY COALESCE(location, '미지정')
        """)
        location_distribution = [dict(row) for row in cursor.fetchall()]
        
        return {
            "ingredient_count": ingredient_count,
            "category_distribution": category_distribution,
            "expiration_status": expiration_status,
            "location_distribution": location_distribution
        }
    except Exception as e:
        st.error(f"통계 조회 오류: {e}")
        return None
    finally:
        conn.close()

# 메인 앱
def main():
    st.title("🍳 레시피 관리 시스템")
    
    # 사이드바 - 앱 정보
    with st.sidebar:
        st.header("📱 앱 정보")
        st.markdown("""
        ### 🍳 레시피 관리 시스템
        
        **주요 기능:**
        - 📦 재료 관리
        - ⏰ 유통기한 알림
        - 🤖 AI 레시피 추천
        - 📊 시각적 분석
        
        **누구나 자유롭게 사용 가능합니다!**
        """)
    
    # 메인 콘텐츠 (인증 없이 바로 접근)
    # 탭으로 기능 구분
    tab1, tab2, tab3, tab4 = st.tabs(["📊 대시보드", "📦 재료 관리", "✨ 레시피 추천", "📈 분석"])
    
    with tab1:
        st.header("📊 대시보드")
        
        # 통계 조회
        stats = get_dashboard_stats()
        if stats and stats.get('ingredient_count', 0) > 0:
            # 메트릭 카드
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 재료", f"{stats['ingredient_count']}개")
            with col2:
                st.metric("카테고리", f"{len(stats['category_distribution'])}종류")
            with col3:
                st.metric("보관 위치", f"{len(stats['location_distribution'])}곳")
            with col4:
                expired_count = next((item['count'] for item in stats['expiration_status'] if item['status'] == '곧 만료'), 0)
                st.metric("유통기한 알림", f"{expired_count}개", delta=None if expired_count == 0 else "주의")
            
            # 차트
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 카테고리별 분포")
                if stats['category_distribution']:
                    df_category = pd.DataFrame(stats['category_distribution'])
                    st.bar_chart(df_category.set_index('category')['count'])
                else:
                    st.info("카테고리 데이터가 없습니다.")
            
            with col2:
                st.subheader("⏰ 유통기한 현황")
                if stats['expiration_status']:
                    df_expiration = pd.DataFrame(stats['expiration_status'])
                    st.bar_chart(df_expiration.set_index('status')['count'])
                else:
                    st.info("유통기한 데이터가 없습니다.")
        else:
            st.info("아직 등록된 재료가 없습니다. 재료를 추가하면 대시보드 정보를 확인할 수 있습니다.")
    
    with tab2:
        st.header("📦 재료 관리")
        
        # 재료 추가 폼
        with st.expander("➕ 새 재료 추가", expanded=False):
            with st.form("add_ingredient_form"):
                col1, col2 = st.columns(2)
                with col1:
                    ingredient_name = st.text_input("재료 이름", placeholder="예: 양파, 닭가슴살")
                    quantity = st.number_input("수량", min_value=0.01, step=0.01)
                    location = st.selectbox("보관 위치", ["냉장실", "냉동실", "상온", "기타"])
                with col2:
                    purchase_date = st.date_input("구매일", value=datetime.now().date())
                    expiration_date = st.date_input("유통기한")
                
                add_btn = st.form_submit_button("재료 추가")
                
                if add_btn:
                    if ingredient_name and quantity and expiration_date:
                        success, message = add_ingredient(
                            ingredient_name,
                            quantity,
                            purchase_date.strftime('%Y-%m-%d'),
                            expiration_date.strftime('%Y-%m-%d'),
                            location
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("모든 필수 항목을 입력해주세요.")
        
        # 재료 목록
        st.subheader("📋 보유 재료 목록")
        ingredients = get_all_ingredients()
        
        if ingredients:
            for ing in ingredients:
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        # 유통기한에 따른 색상 표시
                        try:
                            exp_date = datetime.strptime(ing['expiration_date'], '%Y-%m-%d')
                            days_left = (exp_date - datetime.now()).days
                            
                            if days_left <= 0:
                                status_color = "🔴"
                                status_text = "만료됨"
                            elif days_left <= 2:
                                status_color = "🔴"
                                status_text = "곧 만료"
                            elif days_left <= 5:
                                status_color = "🟡"
                                status_text = "주의"
                            else:
                                status_color = "🟢"
                                status_text = "신선함"
                        except ValueError:
                            status_color = "⚪"
                            status_text = "날짜 오류"
                        
                        st.write(f"**{ing['ingredient_name']}** {status_color} {status_text}")
                        st.write(f"수량: {ing['quantity']}{ing['unit'] or '개'} | 위치: {ing['location']} | 유통기한: {ing['expiration_date']}")
                    
                    with col2:
                        st.write("")  # 공간 확보
                    
                    with col3:
                        if st.button("삭제", key=f"del_{ing['user_ingredient_id']}"):
                            success, message = delete_ingredient(ing['user_ingredient_id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    
                    st.divider()
        else:
            st.info("아직 재료가 없습니다. 재료를 추가해주세요!")
    
    with tab3:
        st.header("✨ GPT 레시피 추천")
        
        if not OPENAI_API_KEY:
            st.warning("OpenAI API 키가 설정되지 않아 레시피 추천 기능을 사용할 수 없습니다.")
        else:
            # 추천 옵션
            col1, col2 = st.columns(2)
            with col1:
                allergies_input = st.text_input("알레르기 (쉼표로 구분)", placeholder="예: 땅콩, 새우")
            with col2:
                preferences_input = st.text_input("선호사항 (쉼표로 구분)", placeholder="예: 매운맛, 간단한 요리")
            
            if st.button("🤖 GPT 레시피 추천받기"):
                allergies = [a.strip() for a in allergies_input.split(',') if a.strip()] if allergies_input else []
                preferences = [p.strip() for p in preferences_input.split(',') if p.strip()] if preferences_input else []
                
                with st.spinner("GPT가 맞춤 레시피를 생성하고 있습니다..."):
                    recommendation = recommend_recipes(allergies, preferences)
                
                st.subheader("🍳 추천 레시피")
                st.markdown(recommendation)
    
    with tab4:
        st.header("📈 분석")
        st.info("이 섹션에서는 영양 분석, 식단 계획, 가격 분석 등의 고급 기능을 제공할 예정입니다.")
        
        # 간단한 분석 예시
        ingredients = get_all_ingredients()
        if ingredients:
            st.subheader("📊 재료 분석")
            
            # 유통기한 분석
            expired_count = 0
            soon_expired_count = 0
            fresh_count = 0
            
            for ing in ingredients:
                try:
                    exp_date = datetime.strptime(ing['expiration_date'], '%Y-%m-%d')
                    days_left = (exp_date - datetime.now()).days
                    
                    if days_left <= 0:
                        expired_count += 1
                    elif days_left <= 3:
                        soon_expired_count += 1
                    else:
                        fresh_count += 1
                except ValueError:
                    # 날짜 파싱 오류가 있는 경우 신선함으로 분류
                    fresh_count += 1
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("만료된 재료", f"{expired_count}개", delta=f"-{expired_count}" if expired_count > 0 else None)
            with col2:
                st.metric("곧 만료될 재료", f"{soon_expired_count}개", delta=f"-{soon_expired_count}" if soon_expired_count > 0 else None)
            with col3:
                st.metric("신선한 재료", f"{fresh_count}개", delta=f"+{fresh_count}" if fresh_count > 0 else None)
            
            if expired_count > 0 or soon_expired_count > 0:
                st.warning("⚠️ 만료되었거나 곧 만료될 재료가 있습니다. 빠른 사용을 권장합니다!")
        else:
            st.info("재료를 추가하면 분석 정보를 확인할 수 있습니다.")

if __name__ == "__main__":
    main()