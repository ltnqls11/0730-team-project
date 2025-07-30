import requests
import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import os
import json
import time
from openai import OpenAI
import random
import threading

# API 설정 - 환경변수에서 읽기
SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

# 클라이언트 초기화
@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("🔑 Supabase 설정이 필요합니다!")
        st.info("""
        **설정 방법:**
        1. `.streamlit/secrets.toml` 파일 생성
        2. 또는 환경변수 `SUPABASE_URL`, `SUPABASE_KEY` 설정
        """)
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def init_openai():
    if OPENAI_API_KEY:
        return OpenAI(api_key=OPENAI_API_KEY)
    return None

supabase = init_supabase()
openai_client = init_openai()

# 페이지 설정
st.set_page_config(
    page_title="🍳 AI 레시피 추천",
    page_icon="🍳",
    layout="wide"
)

st.title("🍳 AI 레시피 추천 앱")



st.markdown("---")

# 레시피 카테고리 설정
RECIPE_CATEGORIES = {
    "한식": {
        "ingredients": ["김치", "쌀", "두부", "콩나물", "시금치", "당근", "양파", "마늘", "생강", "고추장", "된장", "간장", "참기름", "돼지고기", "소고기", "닭고기"],
        "dishes": ["볶음밥", "찌개", "국", "무침", "조림", "구이", "전"]
    },
    "중식": {
        "ingredients": ["면", "양배추", "죽순", "목이버섯", "간장", "굴소스", "참기름", "돼지고기", "새우", "달걀", "파", "마늘", "생강"],
        "dishes": ["볶음면", "탕수육", "짜장면", "볶음밥", "딤섬", "찜"]
    },
    "양식": {
        "ingredients": ["파스타", "토마토", "치즈", "올리브오일", "바질", "마늘", "양파", "버섯", "닭고기", "베이컨", "크림", "와인"],
        "dishes": ["파스타", "리조또", "스테이크", "샐러드", "수프", "그라탕"]
    },
    "일식": {
        "ingredients": ["쌀", "김", "간장", "미소", "두부", "무", "오이", "연어", "참치", "새우", "와사비", "생강"],
        "dishes": ["초밥", "라멘", "우동", "덮밥", "미소시루", "테리야키"]
    },
    "디저트": {
        "ingredients": ["밀가루", "설탕", "달걀", "버터", "우유", "바닐라", "초콜릿", "딸기", "바나나", "견과류"],
        "dishes": ["케이크", "쿠키", "마카롱", "푸딩", "타르트", "무스"]
    }
}

# 사이드바 - 기능 선택
with st.sidebar:
    st.header("📋 메뉴")
    menu = st.selectbox(
        "기능을 선택하세요",
        ["레시피 검색", "레시피 추가", "레시피 관리", "AI 레시피 생성"]
    )

# 데이터베이스 테이블 생성 함수
def create_table_if_not_exists():
    try:
        supabase.table('recipes').select('*').limit(1).execute()
    except:
        st.error("Supabase 테이블을 확인해주세요. 'recipes' 테이블이 필요합니다.")
        st.info("""
        Supabase에서 다음 SQL로 테이블을 생성하세요:
        
        ```sql
        CREATE TABLE recipes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            instructions TEXT NOT NULL,
            cooking_time INTEGER,
            difficulty TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        ```
        """)

# 한글 폰트 등록 함수
@st.cache_resource
def register_korean_font():
    """한글 폰트를 등록합니다."""
    try:
        # Windows 시스템 폰트 경로들
        font_paths = [
            "C:/Windows/Fonts/malgun.ttf",  # 맑은 고딕
            "C:/Windows/Fonts/gulim.ttc",   # 굴림
            "C:/Windows/Fonts/batang.ttc",  # 바탕
            "C:/Windows/Fonts/NanumGothic.ttf",  # 나눔고딕 (설치된 경우)
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('Korean', font_path))
                    return True
                except:
                    continue
        
        # 시스템 폰트를 찾지 못한 경우 기본 폰트 사용
        st.warning("⚠️ 한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다.")
        return False
        
    except Exception as e:
        st.warning(f"폰트 등록 중 오류: {e}")
        return False

# PDF 생성 함수 (한글 지원)
def create_pdf(recipe_data):
    """한글을 지원하는 PDF 생성 함수"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=50, bottomMargin=50)
    
    # 한글 폰트 등록
    font_registered = register_korean_font()
    
    # 스타일 설정
    styles = getSampleStyleSheet()
    
    if font_registered:
        # 한글 폰트가 등록된 경우 커스텀 스타일 생성
        korean_title = ParagraphStyle(
            'KoreanTitle',
            parent=styles['Title'],
            fontName='Korean',
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        korean_heading = ParagraphStyle(
            'KoreanHeading',
            parent=styles['Heading2'],
            fontName='Korean',
            fontSize=14,
            spaceBefore=12,
            spaceAfter=6
        )
        
        korean_normal = ParagraphStyle(
            'KoreanNormal',
            parent=styles['Normal'],
            fontName='Korean',
            fontSize=11,
            leading=16,
            spaceAfter=6
        )
    else:
        # 기본 폰트 사용
        korean_title = styles['Title']
        korean_heading = styles['Heading2']
        korean_normal = styles['Normal']
    
    story = []
    
    # 제목
    title = Paragraph(f"<b>{recipe_data['name']}</b>", korean_title)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # 재료 섹션
    ingredients_title = Paragraph("<b>🥘 재료</b>", korean_heading)
    story.append(ingredients_title)
    
    # 재료 내용을 줄바꿈으로 정리
    ingredients_text = recipe_data['ingredients'].replace(',', '<br/>')
    ingredients_content = Paragraph(ingredients_text, korean_normal)
    story.append(ingredients_content)
    story.append(Spacer(1, 15))
    
    # 조리법 섹션
    instructions_title = Paragraph("<b>👨‍🍳 조리법</b>", korean_heading)
    story.append(instructions_title)
    
    # 조리법 내용을 단계별로 정리
    instructions_text = recipe_data['instructions']
    # 숫자로 시작하는 줄을 찾아서 줄바꿈 추가
    import re
    instructions_text = re.sub(r'(\d+\.)', r'<br/><b>\1</b>', instructions_text)
    instructions_content = Paragraph(instructions_text, korean_normal)
    story.append(instructions_content)
    story.append(Spacer(1, 15))
    
    # 추가 정보
    info_items = []
    if recipe_data.get('cooking_time'):
        info_items.append(f"⏰ <b>조리 시간:</b> {recipe_data['cooking_time']}분")
    if recipe_data.get('difficulty'):
        info_items.append(f"📊 <b>난이도:</b> {recipe_data['difficulty']}")
    
    if info_items:
        info_title = Paragraph("<b>📋 요리 정보</b>", korean_heading)
        story.append(info_title)
        
        for item in info_items:
            info_paragraph = Paragraph(item, korean_normal)
            story.append(info_paragraph)
    
    # 푸터 추가
    story.append(Spacer(1, 30))
    footer = Paragraph(
        "<i>🍳 AI 레시피 추천 앱에서 생성된 레시피입니다.</i>", 
        korean_normal
    )
    story.append(footer)
    
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"PDF 생성 중 오류가 발생했습니다: {e}")
        # 오류 발생 시 간단한 텍스트 PDF 생성
        return create_simple_pdf(recipe_data)

def create_simple_pdf(recipe_data):
    """오류 발생 시 사용할 간단한 PDF 생성 함수"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 제목
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"Recipe: {recipe_data['name']}")
    
    # 내용을 영어로 변환하여 표시
    y_position = height - 100
    c.setFont("Helvetica", 12)
    
    # 간단한 텍스트로 내용 표시
    lines = [
        "Ingredients:",
        recipe_data['ingredients'][:100] + "..." if len(recipe_data['ingredients']) > 100 else recipe_data['ingredients'],
        "",
        "Instructions:",
        recipe_data['instructions'][:200] + "..." if len(recipe_data['instructions']) > 200 else recipe_data['instructions'],
        "",
        f"Cooking Time: {recipe_data.get('cooking_time', 'N/A')} minutes",
        f"Difficulty: {recipe_data.get('difficulty', 'N/A')}"
    ]
    
    for line in lines:
        if y_position < 50:
            break
        c.drawString(50, y_position, line[:80])  # 한 줄에 최대 80자
        y_position -= 20
    
    c.save()
    buffer.seek(0)
    return buffer

# AI 레시피 생성 함수들
def test_openai_connection():
    """개선된 OpenAI API 연결 테스트"""
    try:
        # 1단계: 기본 인터넷 연결 확인
        st.info("1️⃣ 기본 인터넷 연결 확인 중...")
        try:
            response = requests.get("https://httpbin.org/get", timeout=10)
            if response.status_code == 200:
                st.success("✅ 기본 인터넷 연결 정상")
            else:
                st.error("❌ 기본 인터넷 연결 문제")
                return False
        except requests.exceptions.RequestException as e:
            st.error(f"❌ 인터넷 연결 실패: {e}")
            st.info("💡 해결책: Wi-Fi 재연결, 이더넷 케이블 확인, 라우터 재시작")
            return False
        
        # 2단계: OpenAI 도메인 연결 확인
        st.info("2️⃣ OpenAI 서버 연결 확인 중...")
        try:
            response = requests.get("https://api.openai.com", timeout=15)
            st.success("✅ OpenAI 서버 연결 가능")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ OpenAI 서버 연결 실패: {e}")
            st.warning("""
            🌐 **네트워크 차단 문제로 보입니다**
            
            **해결 방법:**
            1. VPN 사용 (ProtonVPN, Windscribe 등)
            2. DNS 변경 (8.8.8.8, 1.1.1.1)
            3. 방화벽에서 Python 허용
            4. 프록시 설정 확인
            """)
            return False
        
        # 3단계: OpenAI API 키 테스트
        st.info("3️⃣ OpenAI API 키 테스트 중...")
        
        if not openai_client:
            st.error("❌ OpenAI 클라이언트가 초기화되지 않았습니다.")
            return False
        
        # 매우 간단한 API 호출로 테스트
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5,
            timeout=20
        )
        
        if response.choices:
            st.success("✅ OpenAI API 연결 성공!")
            st.info(f"테스트 응답: {response.choices[0].message.content}")
            return True
        else:
            st.error("❌ OpenAI API 응답이 비어있습니다.")
            return False
            
    except Exception as e:
        error_msg = str(e).lower()
        st.error(f"❌ OpenAI API 연결 실패: {e}")
        
        # 구체적인 해결책 제시
        if any(keyword in error_msg for keyword in ["connection", "network", "timeout", "unreachable"]):
            st.error("🌐 **네트워크 연결 문제**")
            st.info("""
            **즉시 시도할 방법:**
            1. VPN 켜기/끄기 또는 다른 서버로 변경
            2. DNS를 8.8.8.8 또는 1.1.1.1로 변경
            3. 방화벽에서 Python/Streamlit 허용
            4. 라우터 재시작
            5. 모바일 핫스팟으로 테스트
            """)
            
        elif any(keyword in error_msg for keyword in ["authentication", "401", "invalid", "api"]):
            st.error("🔑 **API 키 문제**")
            st.info("""
            **해결 방법:**
            1. OpenAI 웹사이트에서 새 API 키 발급
            2. secrets.toml 파일의 키 값 재확인
            3. API 키 앞뒤 공백 제거
            """)
            
        elif any(keyword in error_msg for keyword in ["quota", "billing", "exceeded"]):
            st.error("💳 **사용량/결제 문제**")
            st.info("OpenAI 대시보드에서 크레딧 잔액과 사용량 한도를 확인해주세요.")
            
        return False

# OpenAI 클라이언트 초기화도 개선
@st.cache_resource
def init_openai():
    """개선된 OpenAI 클라이언트 초기화"""
    if not OPENAI_API_KEY:
        st.warning("⚠️ OpenAI API 키가 설정되지 않았습니다.")
        st.info("""
        **설정 방법:**
        1. `.streamlit/secrets.toml` 파일 생성
        2. 다음 내용 추가: `OPENAI_API_KEY = "sk-your-key-here"`
        """)
        return None
    
    try:
        # 연결 설정 최적화
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=30.0,
            max_retries=2,
            # 프록시 설정이 필요한 경우 추가
            # http_client=httpx.Client(proxies="http://proxy:port")
        )
        return client
    except Exception as e:
        st.error(f"OpenAI 클라이언트 초기화 실패: {e}")
        return None

# 추가: 네트워크 진단 함수
def diagnose_network():
    """상세 네트워크 진단"""
    st.subheader("🔧 네트워크 진단 도구")
    
    if st.button("🔍 상세 진단 시작"):
        with st.spinner("네트워크 진단 중..."):
            
            # 기본 연결 테스트
            st.write("### 1. 기본 연결 테스트")
            test_urls = [
                ("Google", "https://www.google.com"),
                ("Cloudflare", "https://1.1.1.1"),
                ("GitHub", "https://api.github.com"),
                ("OpenAI", "https://api.openai.com")
            ]
            
            for name, url in test_urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        st.success(f"✅ {name}: 연결 성공")
                    else:
                        st.warning(f"⚠️ {name}: 상태 코드 {response.status_code}")
                except requests.exceptions.Timeout:
                    st.error(f"❌ {name}: 타임아웃")
                except requests.exceptions.ConnectionError:
                    st.error(f"❌ {name}: 연결 실패")
                except Exception as e:
                    st.error(f"❌ {name}: {e}")
            
            # DNS 테스트
            st.write("### 2. DNS 테스트")
            try:
                import socket
                ip = socket.gethostbyname("api.openai.com")
                st.success(f"✅ OpenAI DNS 해석: {ip}")
            except:
                st.error("❌ DNS 해석 실패")
                st.info("DNS를 8.8.8.8 또는 1.1.1.1로 변경해보세요.")
            
            # 권장사항
            st.write("### 3. 권장 해결책")
            st.info("""
            **우선순위별 해결 방법:**
            
            1. **VPN 사용**: ProtonVPN, Windscribe 등 무료 VPN 시도
            2. **DNS 변경**: 8.8.8.8, 8.8.4.4 또는 1.1.1.1, 1.0.0.1
            3. **방화벽 설정**: Windows Defender에서 Python 허용
            4. **모바일 핫스팟**: 임시로 폰의 핫스팟 사용
            5. **네트워크 재시작**: 라우터/모뎀 전원 재시작
            """)

def generate_recipe_with_openai(category, ingredients, dish_type):
    """OpenAI API로 레시피 생성"""
    if not openai_client:
        st.error("OpenAI 클라이언트가 초기화되지 않았습니다.")
        return None
    
    # API 키 확인 (디버그용)
    api_key = OPENAI_API_KEY
    if not api_key:
        st.error("OpenAI API 키가 설정되지 않았습니다.")
        return None
    
    if not api_key.startswith('sk-'):
        st.error("올바르지 않은 OpenAI API 키 형식입니다.")
        return None
        
    try:
        selected_ingredients = random.sample(ingredients, min(6, len(ingredients)))
        
        prompt = f"""
다음 조건으로 {category} {dish_type} 레시피를 생성해주세요:

주요 재료: {', '.join(selected_ingredients)}

응답은 반드시 다음 JSON 형식으로만 답변해주세요:
{{
    "name": "요리 이름",
    "ingredients": "재료 목록 (구체적인 양과 함께)",
    "instructions": "단계별 조리법 (1. 2. 3. 형식으로 번호를 매겨서)",
    "cooking_time": 조리시간(분, 숫자만),
    "difficulty": "쉬움/보통/어려움 중 하나"
}}

실제로 만들 수 있는 현실적인 레시피로, 한국어로 작성해주세요.
조리법은 반드시 "1. 첫 번째 단계 2. 두 번째 단계 3. 세 번째 단계" 형식으로 작성해주세요.
"""
        
        # API 호출 시도
        st.info("OpenAI API 호출 중...")
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 전문 요리사입니다. 요청받은 형식의 JSON으로만 답변하세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.8,
            timeout=30  # 30초 타임아웃 추가
        )
        
        recipe_text = response.choices[0].message.content.strip()
        
        if "```json" in recipe_text:
            recipe_text = recipe_text.split("```json")[1].split("```")[0]
        elif "```" in recipe_text:
            recipe_text = recipe_text.split("```")[1]
        
        recipe_data = json.loads(recipe_text)
        return recipe_data
        
    except Exception as e:
        error_message = str(e)
        st.error(f"AI 레시피 생성 상세 오류: {error_message}")
        
        # 일반적인 오류 유형별 해결책 제시
        if "connection" in error_message.lower():
            st.info("🌐 네트워크 연결을 확인해주세요. 프록시나 방화벽 설정을 확인해보세요.")
        elif "authentication" in error_message.lower() or "401" in error_message:
            st.info("🔑 OpenAI API 키를 확인해주세요. 유효한 키인지 확인해보세요.")
        elif "quota" in error_message.lower() or "billing" in error_message.lower():
            st.info("💳 OpenAI 계정의 잔액이나 사용량 한도를 확인해주세요.")
        elif "timeout" in error_message.lower():
            st.info("⏰ 네트워크가 느려서 타임아웃이 발생했습니다. 다시 시도해주세요.")
        
        return None

def save_recipe_to_db(recipe_data):
    """생성된 레시피를 데이터베이스에 저장"""
    try:
        response = supabase.table('recipes').insert(recipe_data).execute()
        return response.data is not None
    except Exception as e:
        st.error(f"DB 저장 오류: {e}")
        return False

def format_instructions(instructions):
    """조리법을 1. 2. 3. 형식으로 줄바꿈해서 포맷팅"""
    if not instructions:
        return instructions
    
    import re
    # 1. 2. 3. 형식의 번호를 찾아서 줄바꿈 추가
    formatted = re.sub(r'(\d+\.)', r'\n\1', instructions)
    # 첫 번째 줄의 앞쪽 줄바꿈 제거
    formatted = formatted.lstrip('\n')
    return formatted





# 레시피 검색 기능
def search_recipes():
    st.header("🔍 레시피 검색")
    
    # 검색 입력과 버튼을 완벽하게 정렬하기 위한 CSS
    st.markdown("""
    <style>
    div[data-testid="column"]:nth-child(2) > div > div > button {
        margin-top: 1.875rem !important;
        height: 2.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        ingredients_input = st.text_input(
            "가지고 있는 재료를 입력하세요 (쉼표로 구분)",
            placeholder="예: 양파, 감자, 당근"
        )
    with col2:
        # 라벨 공간만큼 여백 추가
        st.markdown('<div style="height: 1.875rem;"></div>', unsafe_allow_html=True)
        search_button = st.button("🔍 검색", type="primary")
    
    if search_button and ingredients_input:
        ingredients_list = [ing.strip() for ing in ingredients_input.split(',')]
        
        try:
            response = supabase.table('recipes').select('*').execute()
            
            if response.data:
                matching_recipes = []
                
                for recipe in response.data:
                    recipe_ingredients = recipe['ingredients'].lower()
                    match_count = sum(1 for ing in ingredients_list 
                                    if ing.lower() in recipe_ingredients)
                    
                    if match_count > 0:
                        recipe['match_score'] = match_count
                        matching_recipes.append(recipe)
                
                matching_recipes.sort(key=lambda x: x['match_score'], reverse=True)
                
                if matching_recipes:
                    st.success(f"🎉 {len(matching_recipes)}개의 레시피를 찾았습니다!")
                    
                    for recipe in matching_recipes:
                        with st.expander(f"📖 {recipe['name']} (매칭: {recipe['match_score']}개 재료)"):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write("**재료:**")
                                st.write(recipe['ingredients'])
                                st.write("**조리법:**")
                                st.write(format_instructions(recipe['instructions']))
                                
                                if recipe.get('cooking_time'):
                                    st.write(f"**조리 시간:** {recipe['cooking_time']}분")
                                if recipe.get('difficulty'):
                                    st.write(f"**난이도:** {recipe['difficulty']}")
                            
                            with col2:
                                pdf_buffer = create_pdf(recipe)
                                st.download_button(
                                    label="📄 PDF 다운로드",
                                    data=pdf_buffer,
                                    file_name=f"{recipe['name']}_레시피.pdf",
                                    mime="application/pdf",
                                    key=f"pdf_{recipe['id']}"
                                )
                                
                                df = pd.DataFrame([recipe])
                                excel_buffer = io.BytesIO()
                                df.to_excel(excel_buffer, index=False, engine='openpyxl')
                                excel_buffer.seek(0)
                                
                                st.download_button(
                                    label="📊 엑셀 다운로드",
                                    data=excel_buffer,
                                    file_name=f"{recipe['name']}_레시피.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"excel_{recipe['id']}"
                                )
                else:
                    st.warning("😅 입력한 재료로 만들 수 있는 레시피를 찾지 못했습니다.")
                    st.info("다른 재료를 입력해보거나 새로운 레시피를 추가해보세요!")
            else:
                st.info("등록된 레시피가 없습니다. 먼저 레시피를 추가해주세요!")
                
        except Exception as e:
            st.error(f"검색 중 오류가 발생했습니다: {str(e)}")

# 레시피 추가 기능
def add_recipe():
    st.header("➕ 새 레시피 추가")
    
    with st.form("recipe_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            recipe_name = st.text_input("레시피 이름 *", placeholder="예: 김치볶음밥")
            cooking_time = st.number_input("조리 시간 (분)", min_value=1, value=30)
        
        with col2:
            difficulty = st.selectbox("난이도", ["쉬움", "보통", "어려움"])
        
        ingredients = st.text_area(
            "재료 *", 
            placeholder="예: 김치 200g, 밥 2공기, 돼지고기 100g, 양파 1개, 대파 1대, 참기름, 김 약간",
            height=100
        )
        
        instructions = st.text_area(
            "조리법 *", 
            placeholder="1. 재료를 준비합니다.\n2. ...",
            height=200
        )
        
        submitted = st.form_submit_button("📝 레시피 추가", type="primary")
        
        if submitted:
            if recipe_name and ingredients and instructions:
                try:
                    data = {
                        'name': recipe_name,
                        'ingredients': ingredients,
                        'instructions': instructions,
                        'cooking_time': cooking_time,
                        'difficulty': difficulty
                    }
                    
                    response = supabase.table('recipes').insert(data).execute()
                    
                    if response.data:
                        st.success("🎉 레시피가 성공적으로 추가되었습니다!")
                        st.balloons()
                    else:
                        st.error("레시피 추가에 실패했습니다.")
                        
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {str(e)}")
            else:
                st.error("필수 항목을 모두 입력해주세요! (*)")

# 모든 레시피 보기
def view_all_recipes():
    st.header("📚 모든 레시피")
    
    try:
        response = supabase.table('recipes').select('*').order('created_at', desc=True).execute()
        
        if response.data:
            st.info(f"총 {len(response.data)}개의 레시피가 등록되어 있습니다.")
            
            col1, col2 = st.columns(2)
            with col1:
                df_all = pd.DataFrame(response.data)
                excel_buffer = io.BytesIO()
                df_all.to_excel(excel_buffer, index=False, engine='openpyxl')
                excel_buffer.seek(0)
                
                st.download_button(
                    label="📊 전체 레시피 엑셀 다운로드",
                    data=excel_buffer,
                    file_name="전체_레시피_목록.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            st.markdown("---")
            
            for recipe in response.data:
                with st.expander(f"📖 {recipe['name']}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write("**재료:**")
                        st.write(recipe['ingredients'])
                        st.write("**조리법:**")
                        st.write(format_instructions(recipe['instructions']))
                        
                        info_cols = st.columns(3)
                        with info_cols[0]:
                            if recipe.get('cooking_time'):
                                st.write(f"⏰ {recipe['cooking_time']}분")
                        with info_cols[1]:
                            if recipe.get('difficulty'):
                                st.write(f"📊 {recipe['difficulty']}")
                        with info_cols[2]:
                            if recipe.get('created_at'):
                                date_str = recipe['created_at'][:10]
                                st.write(f"📅 {date_str}")
                    
                    with col2:
                        pdf_buffer = create_pdf(recipe)
                        st.download_button(
                            label="📄 PDF",
                            data=pdf_buffer,
                            file_name=f"{recipe['name']}_레시피.pdf",
                            mime="application/pdf",
                            key=f"all_pdf_{recipe['id']}"
                        )
                        
                        df_single = pd.DataFrame([recipe])
                        excel_buffer = io.BytesIO()
                        df_single.to_excel(excel_buffer, index=False, engine='openpyxl')
                        excel_buffer.seek(0)
                        
                        st.download_button(
                            label="📊 엑셀",
                            data=excel_buffer,
                            file_name=f"{recipe['name']}_레시피.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"all_excel_{recipe['id']}"
                        )
        else:
            st.info("등록된 레시피가 없습니다.")
            st.markdown("👈 사이드바에서 '레시피 추가'를 선택해 첫 번째 레시피를 등록해보세요!")
            
    except Exception as e:
        st.error(f"레시피를 불러오는 중 오류가 발생했습니다: {str(e)}")

# AI 레시피 생성 기능
def ai_recipe_generator():
    st.header("AI 레시피 생성")
    
    if not openai_client:
        st.error("🔑 OpenAI API 키가 설정되지 않았습니다!")
        st.info("""
        **설정 방법:**
        1. `.streamlit/secrets.toml` 파일에 `OPENAI_API_KEY` 추가
        2. 또는 환경변수 `OPENAI_API_KEY` 설정
        """)
        return
    
    # API 연결 테스트 버튼 추가
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔍 API 연결 테스트"):
            test_openai_connection()
    
    # 현재 레시피 개수 표시
    try:
        response = supabase.table('recipes').select('count', count='exact').execute()
        count = response.count if response.count is not None else 0
        with col2:
            st.info(f"📊 현재 데이터베이스에 {count}개의 레시피가 저장되어 있습니다.")
    except:
        pass
    
    st.markdown("---")
    
    # 탭으로 기능 분리
    tab1, tab2 = st.tabs(["� 랜덤 생성",  "🍳 맞춤 생성"])
    
    with tab1:
        st.subheader("랜덤 레시피 생성")
        
        col1, col2 = st.columns(2)
        with col1:
            batch_category = st.selectbox("생성할 카테고리", ["전체"] + list(RECIPE_CATEGORIES.keys()), key="batch")
        with col2:
            batch_count = st.number_input("생성할 개수", min_value=1, max_value=20, value=5)
        
        if st.button("🎲 랜덤 생성 시작", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            total_generated = 0
            total_saved = 0
            
            categories_to_process = list(RECIPE_CATEGORIES.keys()) if batch_category == "전체" else [batch_category]
            total_tasks = len(categories_to_process) * batch_count
            
            with results_container:
                for i, category in enumerate(categories_to_process):
                    st.write(f"### 📂 {category} 카테고리")
                    
                    for j in range(batch_count):
                        current_task = i * batch_count + j + 1
                        progress = current_task / total_tasks
                        progress_bar.progress(progress)
                        
                        dish_type = random.choice(RECIPE_CATEGORIES[category]["dishes"])
                        status_text.text(f"생성 중: {category} - {dish_type} ({current_task}/{total_tasks})")
                        
                        recipe_data = generate_recipe_with_openai(
                            category,
                            RECIPE_CATEGORIES[category]["ingredients"],
                            dish_type
                        )
                        
                        if recipe_data:
                            total_generated += 1
                            if save_recipe_to_db(recipe_data):
                                total_saved += 1
                                st.success(f"✅ {recipe_data['name']} 저장 완료")
                            else:
                                st.error(f"❌ {recipe_data['name']} 저장 실패")
                        else:
                            st.error(f"❌ {category} {dish_type} 생성 실패")
                        
                        time.sleep(0.5)  # API 레이트 리밋 방지
            
            status_text.text("🎉 랜덤 생성 완료!")
            st.success(f"총 {total_generated}개 생성, {total_saved}개 저장 완료!")
    
    with tab2:
        st.subheader("맞춤 레시피 생성")
        
        custom_ingredients = st.text_input(
            "원하는 재료들을 입력하세요 (쉼표로 구분)",
            placeholder="예: 감자, 양파, 치즈, 베이컨"
        )
        
        custom_count = st.number_input("생성할 레시피 개수", min_value=1, max_value=5, value=2)
        
        if st.button("🍳 맞춤 레시피 생성", type="primary") and custom_ingredients:
            ingredients_list = [ing.strip() for ing in custom_ingredients.split(',')]
            
            for i in range(custom_count):
                with st.spinner(f"맞춤 레시피 생성 중... ({i+1}/{custom_count})"):
                    try:
                        prompt = f"""
다음 재료들을 주로 사용하는 레시피를 생성해주세요:
재료: {', '.join(ingredients_list)}

응답은 반드시 다음 JSON 형식으로만 답변해주세요:
{{
    "name": "요리 이름",
    "ingredients": "재료 목록 (구체적인 양과 함께)",
    "instructions": "단계별 조리법 (1. 2. 3. 형식으로 번호를 매겨서)",
    "cooking_time": 조리시간(분, 숫자만),
    "difficulty": "쉬움/보통/어려움 중 하나"
}}

실제로 만들 수 있는 현실적인 레시피로, 한국어로 작성해주세요.
조리법은 반드시 "1. 첫 번째 단계 2. 두 번째 단계 3. 세 번째 단계" 형식으로 작성해주세요.
"""
                        
                        response = openai_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "당신은 전문 요리사입니다. JSON 형식으로만 답변하세요."},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=1000,
                            temperature=0.8
                        )
                        
                        recipe_text = response.choices[0].message.content.strip()
                        
                        if "```json" in recipe_text:
                            recipe_text = recipe_text.split("```json")[1].split("```")[0]
                        elif "```" in recipe_text:
                            recipe_text = recipe_text.split("```")[1]
                        
                        recipe_data = json.loads(recipe_text)
                        
                        with st.expander(f"🍽️ {recipe_data['name']}", expanded=True):
                            # 이미지와 함께 레시피 표시
                            img_col, content_col, btn_col = st.columns([1, 2, 1])
                            
                            with img_col:
                                # 음식 이미지 표시
                                try:
                                    image_url = get_food_image(recipe_data['name'])
                                    st.image(image_url, caption=recipe_data['name'], use_container_width=True)
                                except Exception as e:
                                    st.info("🖼️ 이미지 로딩 중...")
                            
                            with content_col:
                                st.write(f"**재료:** {recipe_data['ingredients']}")
                                st.write("**조리법:**")
                                st.write(format_instructions(recipe_data['instructions']))
                                st.write(f"**조리시간:** {recipe_data['cooking_time']}분 | **난이도:** {recipe_data['difficulty']}")
                            
                            with col2:
                                if st.button("💾 저장", key=f"save_custom_{i}"):
                                    if save_recipe_to_db(recipe_data):
                                        st.success("저장 완료!")
                                    else:
                                        st.error("저장 실패")
                        
                        time.sleep(1)  # API 딜레이
                        
                    except Exception as e:
                        st.error(f"생성 오류: {e}")

# 메인 실행
def main():
    create_table_if_not_exists()
    
    if menu == "레시피 검색":
        search_recipes()
    elif menu == "레시피 추가":
        add_recipe()
    elif menu == "AI 레시피 생성":
        ai_recipe_generator()
    elif menu == "레시피 관리":
        manage_recipes()
    
    # 푸터
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            🍳 AI 레시피 추천 앱 | Made with Streamlit, Supabase & OpenAI
        </div>
        """, 
        unsafe_allow_html=True
    )

# 레시피 관리 기능
def manage_recipes():
    st.header("🗂️ 레시피 관리")
    
    try:
        response = supabase.table('recipes').select('*').order('created_at', desc=True).execute()
        
        if response.data:
            st.info(f"총 {len(response.data)}개의 레시피가 등록되어 있습니다.")
            
            # 전체 삭제 버튼
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🗑️ 전체 삭제", type="secondary"):
                    if st.session_state.get('confirm_delete_all', False):
                        try:
                            # 모든 레시피 삭제
                            supabase.table('recipes').delete().neq('id', 0).execute()
                            st.success("✅ 모든 레시피가 삭제되었습니다!")
                            st.session_state['confirm_delete_all'] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"삭제 중 오류가 발생했습니다: {e}")
                    else:
                        st.session_state['confirm_delete_all'] = True
                        st.warning("⚠️ 다시 한 번 클릭하면 모든 레시피가 삭제됩니다!")
            
            with col2:
                if st.session_state.get('confirm_delete_all', False):
                    if st.button("❌ 취소"):
                        st.session_state['confirm_delete_all'] = False
                        st.rerun()
            
            st.markdown("---")
            
            # 개별 레시피 관리
            st.subheader("📋 개별 레시피 관리")
            
            # 검색 기능
            search_term = st.text_input("🔍 레시피 검색", placeholder="레시피 이름으로 검색...")
            
            # 필터링
            filtered_recipes = response.data
            if search_term:
                filtered_recipes = [recipe for recipe in response.data 
                                 if search_term.lower() in recipe['name'].lower()]
            
            if filtered_recipes:
                st.write(f"검색 결과: {len(filtered_recipes)}개")
                
                for recipe in filtered_recipes:
                    with st.expander(f"📖 {recipe['name']}", expanded=False):
                        # 레시피 표시
                        content_col, action_col = st.columns([3, 1])
                        
                        with content_col:
                            st.write("**재료:**")
                            st.write(recipe['ingredients'])
                            st.write("**조리법:**")
                            formatted_instructions = format_instructions(recipe['instructions'])
                            st.write(formatted_instructions[:200] + "..." if len(formatted_instructions) > 200 else formatted_instructions)
                            
                            info_cols = st.columns(3)
                            with info_cols[0]:
                                if recipe.get('cooking_time'):
                                    st.write(f"⏰ {recipe['cooking_time']}분")
                            with info_cols[1]:
                                if recipe.get('difficulty'):
                                    st.write(f"📊 {recipe['difficulty']}")
                            with info_cols[2]:
                                if recipe.get('created_at'):
                                    date_str = recipe['created_at'][:10]
                                    st.write(f"📅 {date_str}")
                        
                        with action_col:
                            st.write("**관리**")
                            
                            # 수정 버튼
                            if st.button("✏️ 수정", key=f"edit_{recipe['id']}"):
                                st.session_state[f'editing_{recipe["id"]}'] = True
                                st.rerun()
                            
                            # 삭제 버튼
                            if st.button("🗑️ 삭제", key=f"delete_{recipe['id']}", type="secondary"):
                                if st.session_state.get(f'confirm_delete_{recipe["id"]}', False):
                                    try:
                                        supabase.table('recipes').delete().eq('id', recipe['id']).execute()
                                        st.success(f"✅ '{recipe['name']}' 레시피가 삭제되었습니다!")
                                        st.session_state[f'confirm_delete_{recipe["id"]}'] = False
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"삭제 중 오류가 발생했습니다: {e}")
                                else:
                                    st.session_state[f'confirm_delete_{recipe["id"]}'] = True
                                    st.warning("⚠️ 다시 클릭하면 삭제됩니다!")
                            
                            # 삭제 확인 취소 버튼
                            if st.session_state.get(f'confirm_delete_{recipe["id"]}', False):
                                if st.button("❌ 취소", key=f"cancel_{recipe['id']}"):
                                    st.session_state[f'confirm_delete_{recipe["id"]}'] = False
                                    st.rerun()
                        
                        # 수정 폼
                        if st.session_state.get(f'editing_{recipe["id"]}', False):
                            st.markdown("---")
                            st.subheader("✏️ 레시피 수정")
                            
                            with st.form(f"edit_form_{recipe['id']}"):
                                edit_name = st.text_input("레시피 이름", value=recipe['name'])
                                edit_ingredients = st.text_area("재료", value=recipe['ingredients'], height=100)
                                edit_instructions = st.text_area("조리법", value=recipe['instructions'], height=150)
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    edit_cooking_time = st.number_input("조리 시간 (분)", 
                                                                      value=recipe.get('cooking_time', 30), 
                                                                      min_value=1)
                                with col2:
                                    edit_difficulty = st.selectbox("난이도", 
                                                                 ["쉬움", "보통", "어려움"],
                                                                 index=["쉬움", "보통", "어려움"].index(recipe.get('difficulty', '보통')))
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.form_submit_button("💾 저장", type="primary"):
                                        try:
                                            update_data = {
                                                'name': edit_name,
                                                'ingredients': edit_ingredients,
                                                'instructions': edit_instructions,
                                                'cooking_time': edit_cooking_time,
                                                'difficulty': edit_difficulty
                                            }
                                            
                                            supabase.table('recipes').update(update_data).eq('id', recipe['id']).execute()
                                            st.success("✅ 레시피가 수정되었습니다!")
                                            st.session_state[f'editing_{recipe["id"]}'] = False
                                            time.sleep(1)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"수정 중 오류가 발생했습니다: {e}")
                                
                                with col2:
                                    if st.form_submit_button("❌ 취소"):
                                        st.session_state[f'editing_{recipe["id"]}'] = False
                                        st.rerun()
            else:
                st.info("검색 결과가 없습니다.")
        else:
            st.info("등록된 레시피가 없습니다.")
            st.markdown("👈 사이드바에서 '레시피 추가' 또는 'AI 레시피 생성'을 선택해 레시피를 추가해보세요!")
            
    except Exception as e:
        st.error(f"레시피를 불러오는 중 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()

