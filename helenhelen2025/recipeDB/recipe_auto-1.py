import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from PIL import Image
import io
import openai
import json
import re
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI API 설정
# openai.api_key = st.secrets["OPENAI_API_KEY"]  # Streamlit secrets 사용

class DatabaseManager:
    def __init__(self, db_path: str = "fridge_management.db"):
        self.db_path = db_path
        self.init_database()
        self.add_sample_ingredients_if_needed()
        self.add_sample_recipes_if_needed()
    
    def _get_conn(self):
        """데이터베이스 연결을 반환합니다. 텍스트 팩토리를 str로 설정하여 문자열 인코딩 문제를 해결합니다."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)  # 30초 타임아웃 설정
        conn.text_factory = str  # 모든 텍스트 데이터를 str 타입으로 반환하도록 설정
        conn.execute('PRAGMA journal_mode=WAL')  # WAL 모드로 설정하여 동시 접근 개선
        return conn
        
    def init_database(self):
        """데이터베이스 초기화"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 재료 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                quantity REAL,
                unit TEXT,
                expiry_date DATE,
                purchase_date DATE DEFAULT (date('now')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 레시피 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ingredients TEXT,  -- JSON 형태로 저장
                instructions TEXT,
                cooking_time INTEGER,  -- 분 단위
                servings INTEGER,
                category TEXT,
                difficulty TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_count INTEGER DEFAULT 0
            )
        ''')
        
        # 요리 기록 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cooking_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER,
                ingredients_used TEXT,  -- JSON 형태
                cooking_date DATE DEFAULT (date('now')),
                rating INTEGER,
                notes TEXT,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        
        # 쇼핑 리스트 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shopping_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_name TEXT NOT NULL,
                quantity REAL,
                unit TEXT,
                priority INTEGER DEFAULT 1,
                purchased BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_ingredient(self, name: str, category: str, quantity: float, unit: str, expiry_date: str = None):
        """재료 추가"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ingredients (name, category, quantity, unit, expiry_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, category, quantity, unit, expiry_date))
        
        conn.commit()
        conn.close()
    
    def get_ingredients(self) -> pd.DataFrame:
        """모든 재료 조회"""
        conn = self._get_conn()
        df = pd.read_sql_query('''
            SELECT * FROM ingredients 
            ORDER BY expiry_date ASC, name ASC
        ''', conn)
        conn.close()
        return df
    
    def add_recipe(self, name: str, ingredients: List[Dict], instructions: str, 
                   cooking_time: int, servings: int, category: str, difficulty: str):
        """레시피 추가"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        ingredients_json = json.dumps(ingredients, ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO recipes (name, ingredients, instructions, cooking_time, servings, category, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, ingredients_json, instructions, cooking_time, servings, category, difficulty))
        
        conn.commit()
        conn.close()
    
    def get_recipes(self) -> pd.DataFrame:
        """모든 레시피 조회"""
        conn = self._get_conn()
        df = pd.read_sql_query('SELECT * FROM recipes ORDER BY used_count DESC, created_at DESC', conn)
        conn.close()
        return df
    
    def update_recipe_usage(self, recipe_id: int):
        """레시피 사용 횟수 업데이트"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE recipes SET used_count = used_count + 1 WHERE id = ?', (recipe_id,))
        
        conn.commit()
        conn.close()

    def add_sample_ingredients_if_needed(self):
        """DB에 샘플 재료 15개가 없으면 자동 추가"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM ingredients')
        count = cursor.fetchone()[0]
        if count < 15:
            sample_ingredients = [
                ("달걀", "유제품", 10, "개", (datetime.now()+timedelta(days=5)).date()),
                ("우유", "유제품", 1, "L", (datetime.now()+timedelta(days=3)).date()),
                ("양파", "채소", 3, "개", (datetime.now()+timedelta(days=2)).date()),
                ("감자", "채소", 5, "개", (datetime.now()+timedelta(days=7)).date()),
                ("당근", "채소", 2, "개", (datetime.now()+timedelta(days=4)).date()),
                ("닭가슴살", "육류", 2, "팩", (datetime.now()+timedelta(days=1)).date()),
                ("소고기", "육류", 0.5, "kg", (datetime.now()+timedelta(days=2)).date()),
                ("두부", "유제품", 1, "모", (datetime.now()+timedelta(days=2)).date()),
                ("애호박", "채소", 1, "개", (datetime.now()+timedelta(days=6)).date()),
                ("파프리카", "채소", 2, "개", (datetime.now()+timedelta(days=3)).date()),
                ("버섯", "채소", 1, "팩", (datetime.now()+timedelta(days=2)).date()),
                ("김치", "기타", 0.5, "kg", (datetime.now()+timedelta(days=20)).date()),
                ("밥", "곡류", 2, "공기", (datetime.now()+timedelta(days=1)).date()),
                ("참치캔", "기타", 2, "개", (datetime.now()+timedelta(days=365)).date()),
                ("치즈", "유제품", 5, "장", (datetime.now()+timedelta(days=10)).date()),
            ]
            for name, category, quantity, unit, expiry_date in sample_ingredients:
                cursor.execute('''INSERT INTO ingredients (name, category, quantity, unit, expiry_date) VALUES (?, ?, ?, ?, ?)''', (name, category, quantity, unit, expiry_date))
            conn.commit()
        conn.close()
    
    def add_sample_recipes_if_needed(self):
        """DB에 샘플 레시피 10개가 없으면 자동 추가"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM recipes')
        count = cursor.fetchone()[0]
        if count < 10:
            sample_recipes = [
                {
                    "name": "김치찌개",
                    "ingredients": [
                        {"name": "김치", "quantity": "200", "unit": "g"},
                        {"name": "돼지고기", "quantity": "150", "unit": "g"},
                        {"name": "두부", "quantity": "1/2", "unit": "모"},
                        {"name": "양파", "quantity": "1/2", "unit": "개"},
                        {"name": "대파", "quantity": "1", "unit": "대"}
                    ],
                    "instructions": "1. 김치와 돼지고기를 볶아줍니다.\n2. 물을 넣고 끓입니다.\n3. 두부와 양파를 넣고 10분간 끓입니다.\n4. 대파를 넣고 마무리합니다.",
                    "cooking_time": 25,
                    "servings": 2,
                    "category": "한식",
                    "difficulty": "쉬움"
                },
                {
                    "name": "계란볶음밥",
                    "ingredients": [
                        {"name": "밥", "quantity": "2", "unit": "공기"},
                        {"name": "달걀", "quantity": "3", "unit": "개"},
                        {"name": "양파", "quantity": "1/2", "unit": "개"},
                        {"name": "당근", "quantity": "1/4", "unit": "개"},
                        {"name": "파", "quantity": "2", "unit": "대"}
                    ],
                    "instructions": "1. 달걀을 스크램블로 만듭니다.\n2. 양파와 당근을 볶습니다.\n3. 밥을 넣고 볶아줍니다.\n4. 달걀과 파를 넣고 마무리합니다.",
                    "cooking_time": 15,
                    "servings": 2,
                    "category": "한식",
                    "difficulty": "쉬움"
                },
                {
                    "name": "된장찌개",
                    "ingredients": [
                        {"name": "된장", "quantity": "2", "unit": "큰술"},
                        {"name": "두부", "quantity": "1/2", "unit": "모"},
                        {"name": "애호박", "quantity": "1/4", "unit": "개"},
                        {"name": "양파", "quantity": "1/4", "unit": "개"},
                        {"name": "버섯", "quantity": "3", "unit": "개"}
                    ],
                    "instructions": "1. 된장을 물에 풀어줍니다.\n2. 야채들을 넣고 끓입니다.\n3. 두부를 넣고 5분간 더 끓입니다.\n4. 파를 넣고 마무리합니다.",
                    "cooking_time": 20,
                    "servings": 2,
                    "category": "한식",
                    "difficulty": "쉬움"
                },
                {
                    "name": "닭볶음탕",
                    "ingredients": [
                        {"name": "닭고기", "quantity": "500", "unit": "g"},
                        {"name": "감자", "quantity": "2", "unit": "개"},
                        {"name": "당근", "quantity": "1", "unit": "개"},
                        {"name": "양파", "quantity": "1", "unit": "개"},
                        {"name": "고추장", "quantity": "2", "unit": "큰술"}
                    ],
                    "instructions": "1. 닭고기를 먼저 볶아줍니다.\n2. 야채들을 넣고 함께 볶습니다.\n3. 고추장과 물을 넣고 끓입니다.\n4. 30분간 조려서 완성합니다.",
                    "cooking_time": 45,
                    "servings": 3,
                    "category": "한식",
                    "difficulty": "보통"
                },
                {
                    "name": "스파게티",
                    "ingredients": [
                        {"name": "스파게티면", "quantity": "200", "unit": "g"},
                        {"name": "토마토소스", "quantity": "1", "unit": "캔"},
                        {"name": "양파", "quantity": "1", "unit": "개"},
                        {"name": "마늘", "quantity": "3", "unit": "쪽"},
                        {"name": "올리브오일", "quantity": "2", "unit": "큰술"}
                    ],
                    "instructions": "1. 면을 삶아줍니다.\n2. 양파와 마늘을 볶습니다.\n3. 토마토소스를 넣고 끓입니다.\n4. 삶은 면과 소스를 섞어 완성합니다.",
                    "cooking_time": 20,
                    "servings": 2,
                    "category": "양식",
                    "difficulty": "쉬움"
                },
                {
                    "name": "마파두부",
                    "ingredients": [
                        {"name": "두부", "quantity": "1", "unit": "모"},
                        {"name": "돼지고기", "quantity": "100", "unit": "g"},
                        {"name": "대파", "quantity": "2", "unit": "대"},
                        {"name": "마늘", "quantity": "3", "unit": "쪽"},
                        {"name": "고추기름", "quantity": "1", "unit": "큰술"}
                    ],
                    "instructions": "1. 돼지고기를 볶아줍니다.\n2. 마늘과 대파를 넣고 볶습니다.\n3. 두부를 넣고 조심스럽게 볶습니다.\n4. 양념장을 넣고 마무리합니다.",
                    "cooking_time": 15,
                    "servings": 2,
                    "category": "중식",
                    "difficulty": "보통"
                },
                {
                    "name": "치킨카레",
                    "ingredients": [
                        {"name": "닭가슴살", "quantity": "300", "unit": "g"},
                        {"name": "카레가루", "quantity": "3", "unit": "큰술"},
                        {"name": "양파", "quantity": "1", "unit": "개"},
                        {"name": "감자", "quantity": "1", "unit": "개"},
                        {"name": "당근", "quantity": "1/2", "unit": "개"}
                    ],
                    "instructions": "1. 닭고기를 먼저 볶아줍니다.\n2. 야채들을 넣고 볶습니다.\n3. 물과 카레가루를 넣고 끓입니다.\n4. 20분간 끓여서 완성합니다.",
                    "cooking_time": 30,
                    "servings": 3,
                    "category": "양식",
                    "difficulty": "보통"
                },
                {
                    "name": "일본식 라멘",
                    "ingredients": [
                        {"name": "라멘면", "quantity": "1", "unit": "봉지"},
                        {"name": "달걀", "quantity": "1", "unit": "개"},
                        {"name": "파", "quantity": "2", "unit": "대"},
                        {"name": "김", "quantity": "1", "unit": "장"},
                        {"name": "차슈", "quantity": "3", "unit": "장"}
                    ],
                    "instructions": "1. 육수를 끓입니다.\n2. 면을 삶아줍니다.\n3. 그릇에 면과 육수를 담습니다.\n4. 토핑들을 올려 완성합니다.",
                    "cooking_time": 10,
                    "servings": 1,
                    "category": "일식",
                    "difficulty": "쉬움"
                },
                {
                    "name": "불고기",
                    "ingredients": [
                        {"name": "소고기", "quantity": "300", "unit": "g"},
                        {"name": "양파", "quantity": "1", "unit": "개"},
                        {"name": "당근", "quantity": "1/2", "unit": "개"},
                        {"name": "간장", "quantity": "3", "unit": "큰술"},
                        {"name": "설탕", "quantity": "1", "unit": "큰술"}
                    ],
                    "instructions": "1. 소고기를 양념에 재워둡니다.\n2. 야채들을 준비합니다.\n3. 고기와 야채를 함께 볶습니다.\n4. 간을 맞춰 완성합니다.",
                    "cooking_time": 20,
                    "servings": 2,
                    "category": "한식",
                    "difficulty": "보통"
                },
                {
                    "name": "새우볶음밥",
                    "ingredients": [
                        {"name": "밥", "quantity": "2", "unit": "공기"},
                        {"name": "새우", "quantity": "10", "unit": "마리"},
                        {"name": "달걀", "quantity": "2", "unit": "개"},
                        {"name": "완두콩", "quantity": "50", "unit": "g"},
                        {"name": "간장", "quantity": "2", "unit": "큰술"}
                    ],
                    "instructions": "1. 새우를 볶아줍니다.\n2. 달걀을 스크램블로 만듭니다.\n3. 밥을 넣고 볶습니다.\n4. 완두콩을 넣고 마무리합니다.",
                    "cooking_time": 15,
                    "servings": 2,
                    "category": "중식",
                    "difficulty": "쉬움"
                }
            ]
            
            for recipe in sample_recipes:
                ingredients_json = json.dumps(recipe["ingredients"], ensure_ascii=False)
                cursor.execute('''
                    INSERT INTO recipes (name, ingredients, instructions, cooking_time, servings, category, difficulty)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (recipe["name"], ingredients_json, recipe["instructions"], 
                     recipe["cooking_time"], recipe["servings"], recipe["category"], recipe["difficulty"]))
            
            conn.commit()
        conn.close()
    
    def add_to_shopping_list(self, ingredient_name: str, quantity: float, unit: str, priority: int = 1):
        """쇼핑 리스트에 재료 추가"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 이미 있는 재료인지 확인
        cursor.execute('SELECT id, quantity FROM shopping_list WHERE ingredient_name = ? AND purchased = FALSE', (ingredient_name,))
        existing = cursor.fetchone()
        
        if existing:
            # 기존 수량에 추가
            new_quantity = existing[1] + quantity
            cursor.execute('UPDATE shopping_list SET quantity = ?, priority = ? WHERE id = ?', 
                          (new_quantity, priority, existing[0]))
        else:
            # 새로 추가
            cursor.execute('''
                INSERT INTO shopping_list (ingredient_name, quantity, unit, priority)
                VALUES (?, ?, ?, ?)
            ''', (ingredient_name, quantity, unit, priority))
        
        conn.commit()
        conn.close()
    
    def get_shopping_list(self) -> pd.DataFrame:
        """쇼핑 리스트 조회"""
        conn = self._get_conn()
        df = pd.read_sql_query('''
            SELECT * FROM shopping_list 
            WHERE purchased = FALSE
            ORDER BY priority DESC, created_at ASC
        ''', conn)
        conn.close()
        return df
    
    def update_shopping_item_status(self, item_id: int, purchased: bool):
        """쇼핑 아이템 구매 상태 업데이트"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('UPDATE shopping_list SET purchased = ? WHERE id = ?', (purchased, item_id))
        conn.commit()
        conn.close()
    
    def delete_ingredient(self, ingredient_id: int):
        """특정 재료 삭제"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ingredients WHERE id = ?', (ingredient_id,))
        conn.commit()
        conn.close()
    
    def delete_recipe(self, recipe_id: int):
        """특정 레시피 삭제"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))
        conn.commit()
        conn.close()
    
    def get_expiring_ingredients(self, days: int = 3) -> pd.DataFrame:
        """유통기한 임박 재료 조회"""
        conn = self._get_conn()
        today = datetime.now().date()
        target_date = today + timedelta(days=days)
        
        df = pd.read_sql_query('''
            SELECT * FROM ingredients 
            WHERE expiry_date <= ? AND expiry_date >= ?
            ORDER BY expiry_date ASC
        ''', conn, params=(target_date, today))
        conn.close()
        return df

class RecipeGenerator:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")
        self.client = openai.OpenAI(api_key=api_key)
    
    def generate_recipe_from_ingredients(self, ingredients: List[str], preferences: str = "") -> Dict:
        """재료 기반 레시피 생성"""
        ingredients_text = ", ".join(ingredients)
        
        prompt = f"""
        다음 재료들을 사용해서 집에서 만들 수 있는 간단한 한식 레시피를 추천해주세요:
        재료: {ingredients_text}
        
        {f"추가 요청사항: {preferences}" if preferences else ""}
        
        다음 JSON 형식으로 응답해주세요:
        {{
            "name": "요리 이름",
            "ingredients": [
                {{"name": "재료명", "quantity": "분량", "unit": "단위"}},
                ...
            ],
            "instructions": "조리법 (단계별로 설명)",
            "cooking_time": 조리시간(분),
            "servings": 몇인분,
            "category": "요리 카테고리",
            "difficulty": "쉬움/보통/어려움",
            "tips": "조리 팁"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 한국 요리 전문가입니다. 주어진 재료로 맛있는 집밥 레시피를 추천해주세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            recipe_text = response.choices[0].message.content
            # JSON 부분만 추출
            json_match = re.search(r'\{.*\}', recipe_text, re.DOTALL)
            if json_match:
                # ensure_ascii=False를 사용하여 한글이 유니코드 이스케이프 시퀀스로 변환되지 않도록 함
                recipe_data = json.loads(json_match.group(), strict=False) 
                return recipe_data
            else:
                return None
            
        except Exception as e:
            st.error(f"레시피 생성 중 오류 발생: {str(e)}")
            return None
    
    def analyze_ingredients_from_image(self, image_data: bytes) -> List[Dict]:
        """이미지에서 재료 인식"""
        # 이미지를 base64로 인코딩
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        prompt = """
        이 냉장고 사진을 보고 보이는 재료들을 인식해서 다음 JSON 형식으로 응답해주세요:
        [
            {
                "name": "재료명",
                "category": "카테고리 (채소/과일/육류/유제품/조미료 등)",
                "estimated_quantity": 추정수량,
                "unit": "단위"
            },
            ...
        ]
        
        한국어로 재료명을 작성하고, 명확하게 식별 가능한 재료만 포함해주세요.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            # JSON 부분만 추출
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if json_match:
                # ensure_ascii=False를 사용하여 한글이 유니코드 이스케이프 시퀀스로 변환되지 않도록 함
                ingredients_data = json.loads(json_match.group(), strict=False) 
                return ingredients_data
            else:
                return []
            
        except Exception as e:
            st.error(f"이미지 분석 중 오류 발생: {str(e)}")
            return []

def main():
    st.set_page_config(
        page_title="오늘 뭐 먹지?",
        page_icon="🍚🥗🍳🥘🥒🥕🥩",
        layout="wide"
    )
    
    st.title("🍚 오늘 뭐 먹지? 🥗🍳🥘🥒🥕🥩")
    
    # 데이터베이스 매니저 초기화
    db = DatabaseManager()
    
    # 메인 탭 메뉴 (사이드바 대신 body에 탭으로 변경)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏠 홈", "🥬 재료 관리", "🍳 레시피 추천", 
        "📖 레시피 북", "🛒 쇼핑 리스트", "📝 요리 기록", "📊 분석 대시보드"
    ])
    
    with tab1:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🔄 새로고침", key="refresh_home"):
                st.rerun()
        show_home_page(db)
    
    with tab2:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🔄 새로고침", key="refresh_ingredients"):
                st.rerun()
        show_ingredient_management(db)
    
    with tab3:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🔄 새로고침", key="refresh_recipe_rec"):
                st.rerun()
        show_recipe_recommendation(db)
    
    with tab4:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🔄 새로고침", key="refresh_recipe_book"):
                st.rerun()
        show_recipe_book(db)
    
    with tab5:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🔄 새로고침", key="refresh_shopping"):
                st.rerun()
        show_shopping_list(db)
    
    with tab6:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🔄 새로고침", key="refresh_cooking"):
                st.rerun()
        show_cooking_history(db)
    
    with tab7:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🔄 새로고침", key="refresh_analytics"):
                st.rerun()
        show_analytics_dashboard(db)

def show_home_page(db: DatabaseManager):
    """홈 페이지"""
    # 환영 메시지와 이미지
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 30px;">
        <h1 style="color: white; font-size: 2.5em; margin-bottom: 10px;">🍚 오늘 뭐 먹지? 🥗</h1>
        <p style="color: white; font-size: 1.2em; margin: 0;">맛있는 요리의 시작, 여기서부터!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 요리하는 엄마와 맛있는 음식 이미지 영역
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <div style="font-size: 8em; margin-bottom: 20px;">👩‍🍳</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 맛있는 음식 이모지들
    st.markdown("""
    <div style="text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 15px; margin: 20px 0;">
        <h3 style="color: #333; margin-bottom: 20px;">🍽️ 오늘의 추천 메뉴 🍽️</h3>
        <div style="font-size: 3em; line-height: 1.5;">
            🍲 🥘 🍳 🥗 🍜 🍱 🥙 🌮 🍕 🍝 🥞 🧆
        </div>
        <p style="color: #666; margin-top: 15px;">다양한 요리로 가족의 행복을 만들어보세요!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 통계 정보를 카드 형태로 표시
    st.markdown("### 📊 나의 요리 현황")
    
    ingredients_df = db.get_ingredients()
    recipes_df = db.get_recipes()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); padding: 20px; border-radius: 15px; text-align: center;">
            <div style="font-size: 2.5em; margin-bottom: 10px;">🥬</div>
            <h3 style="color: white; margin: 0;">보유 재료</h3>
            <h2 style="color: white; margin: 5px 0;">{}</h2>
        </div>
        """.format(len(ingredients_df)), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); padding: 20px; border-radius: 15px; text-align: center;">
            <div style="font-size: 2.5em; margin-bottom: 10px;">📖</div>
            <h3 style="color: white; margin: 0;">저장된 레시피</h3>
            <h2 style="color: white; margin: 5px 0;">{}</h2>
        </div>
        """.format(len(recipes_df)), unsafe_allow_html=True)
    
    with col3:
        # 유통기한 임박 재료
        expiring_count = 0
        if not ingredients_df.empty:
            today = datetime.now().date()
            ingredients_df['expiry_date'] = pd.to_datetime(ingredients_df['expiry_date']).dt.date
            expiring_soon = ingredients_df[
                (ingredients_df['expiry_date'] <= today + timedelta(days=3)) & 
                (ingredients_df['expiry_date'] >= today)
            ]
            expiring_count = len(expiring_soon)
        
        color = "#ff6b6b" if expiring_count > 0 else "#51cf66"
        st.markdown("""
        <div style="background: linear-gradient(135deg, {} 0%, {} 100%); padding: 20px; border-radius: 15px; text-align: center;">
            <div style="font-size: 2.5em; margin-bottom: 10px;">⏰</div>
            <h3 style="color: white; margin: 0;">유통기한 임박</h3>
            <h2 style="color: white; margin: 5px 0;">{}</h2>
        </div>
        """.format(color, color, expiring_count), unsafe_allow_html=True)
    
    # 최근 레시피
    if not recipes_df.empty:
        st.subheader("🔥 인기 레시피 TOP 3")
        top_recipes = recipes_df.head(3)
        for _, recipe in top_recipes.iterrows():
            with st.expander(f"{recipe['name']} (사용횟수: {recipe['used_count']}회)"):
                st.write(f"**카테고리:** {recipe['category']}")
                st.write(f"**난이도:** {recipe['difficulty']}")
                st.write(f"**조리시간:** {recipe['cooking_time']}분")
    
    # 유통기한 임박 알림
    if not ingredients_df.empty:
        today = datetime.now().date()
        ingredients_df['expiry_date'] = pd.to_datetime(ingredients_df['expiry_date']).dt.date
        expiring_soon = ingredients_df[
            (ingredients_df['expiry_date'] <= today + timedelta(days=3)) & 
            (ingredients_df['expiry_date'] >= today)
        ]
        
        if not expiring_soon.empty:
            st.warning("⚠️ 유통기한이 임박한 재료가 있습니다!")
            for _, ingredient in expiring_soon.iterrows():
                days_left = (ingredient['expiry_date'] - today).days
                st.write(f"• {ingredient['name']}: {days_left}일 남음")

def show_ingredient_management(db: DatabaseManager):
    """재료 관리 페이지"""
    st.header("🥬 재료 관리")
    
    tab1, tab2, tab3, tab4 = st.tabs(["사진으로 추가", "직접 입력", "재료 목록", "🗑️ 재료 삭제"])
    
    with tab1:
        st.subheader("📸 사진으로 재료 인식")
        
        # OpenAI API 키 입력 UI 제거
        
        uploaded_file = st.file_uploader("냉장고 사진을 업로드하세요", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file is not None:
            # 이미지 표시
            image = Image.open(uploaded_file)
            st.image(image, caption="업로드된 이미지", use_column_width=True)
            
            if st.button("재료 인식하기"):
                with st.spinner("이미지에서 재료를 인식하는 중..."):
                    recipe_gen = RecipeGenerator()
                    ingredients = recipe_gen.analyze_ingredients_from_image(uploaded_file.getvalue())
                    
                    if ingredients:
                        st.success(f"{len(ingredients)}개의 재료를 인식했습니다!")
                        
                        # 인식된 재료들을 데이터프레임으로 표시
                        df = pd.DataFrame(ingredients)
                        edited_df = st.data_editor(
                            df,
                            column_config={
                                "name": "재료명",
                                "category": "카테고리",
                                "estimated_quantity": "수량",
                                "unit": "단위"
                            },
                            num_rows="dynamic"
                        )
                        
                        if st.button("선택된 재료들 저장"):
                            for _, row in edited_df.iterrows():
                                # pandas DataFrame에서 NaN 값은 float로 처리될 수 있으므로 None으로 명시적으로 변환
                                expiry_date_str = None
                                if 'expiry_date' in row and pd.notna(row['expiry_date']):
                                    # 날짜 형식을 'YYYY-MM-DD'로 보장
                                    expiry_date_str = pd.to_datetime(row['expiry_date']).strftime('%Y-%m-%d')
                                    
                                db.add_ingredient(
                                    name=row['name'],
                                    category=row['category'],
                                    quantity=row['estimated_quantity'],
                                    unit=row['unit'],
                                    expiry_date=expiry_date_str
                                )
                            st.success("재료들이 저장되었습니다!")
                            st.rerun()
                    else:
                        st.error("재료를 인식할 수 없습니다. 다른 이미지를 시도해보세요.")
    
    with tab2:
        st.subheader("✏️ 직접 입력")
        
        with st.form("add_ingredient_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("재료명")
                category = st.selectbox("카테고리", 
                    ["채소", "과일", "육류", "해산물", "유제품", "곡류", "조미료", "기타"])
            
            with col2:
                quantity = st.number_input("수량", min_value=0.0, step=0.1)
                unit = st.selectbox("단위", ["개", "g", "kg", "ml", "L", "컵", "큰술", "작은술"])
            
            expiry_date = st.date_input("유통기한 (선택사항)", value=None)
            
            submitted = st.form_submit_button("재료 추가")
            
            if submitted and name:
                db.add_ingredient(
                    name=name,
                    category=category,
                    quantity=quantity,
                    unit=unit,
                    expiry_date=expiry_date.isoformat() if expiry_date else None
                )
                st.success(f"{name}이(가) 추가되었습니다!")
                st.rerun()
    
    with tab3:
        st.subheader("📋 보유 재료 목록")
        
        ingredients_df = db.get_ingredients()
        
        if not ingredients_df.empty:
            # 뷰 선택 옵션
            view_type = st.radio("보기 방식", ["카드 뷰", "테이블 뷰"], horizontal=True)
            
            # 카테고리별 필터
            categories = ["전체"] + list(ingredients_df['category'].unique())
            selected_category = st.selectbox("카테고리 필터", categories)
            
            if selected_category != "전체":
                filtered_df = ingredients_df[ingredients_df['category'] == selected_category]
            else:
                filtered_df = ingredients_df.copy()
            
            # 유통기한으로 정렬
            if 'expiry_date' in filtered_df.columns:
                filtered_df['expiry_date'] = pd.to_datetime(filtered_df['expiry_date'])
                filtered_df = filtered_df.sort_values(by='expiry_date') # Sort by expiry date

            if view_type == "테이블 뷰":
                # 수량을 소수점 첫째자리까지만 표시
                display_df = filtered_df.copy()
                display_df['quantity'] = display_df['quantity'].round(1)
                st.dataframe(display_df.style.apply(highlight_expiring_ingredients, axis=1))
            else: # 카드 뷰
                display_ingredients_as_cards(filtered_df)
        else:
            st.info("현재 냉장고에 재료가 없습니다. 새 재료를 추가해주세요!")

    with tab4:
        st.subheader("🗑️ 재료 삭제")
        ingredients_df = db.get_ingredients()
        
        if not ingredients_df.empty:
            ingredients_df_display = ingredients_df[['id', 'name', 'category', 'quantity', 'unit', 'expiry_date']]
            
            st.dataframe(ingredients_df_display)
            
            ingredient_to_delete_id = st.number_input("삭제할 재료의 ID를 입력하세요", min_value=1, format="%d")
            
            if st.button("재료 삭제"):
                # ID가 유효한지 확인
                if ingredient_to_delete_id in ingredients_df['id'].values:
                    db.delete_ingredient(ingredient_to_delete_id)
                    st.success(f"ID {ingredient_to_delete_id}번 재료가 삭제되었습니다.")
                    st.rerun()
                else:
                    st.error("유효하지 않은 재료 ID입니다.")
        else:
            st.info("삭제할 재료가 없습니다.")

def highlight_expiring_ingredients(row):
    """유통기한 임박 재료 강조 (Streamlit Dataframe styling)"""
    today = datetime.now().date()
    if pd.notna(row['expiry_date']):
        expiry_date = pd.to_datetime(row['expiry_date']).date()
        if today <= expiry_date <= today + timedelta(days=3):
            return ['background-color: #ffe0b2'] * len(row)  # 주황색 계열
        elif expiry_date < today:
            return ['background-color: #ffcdd2'] * len(row)  # 빨간색 계열
    return [''] * len(row)

def display_ingredients_as_cards(df: pd.DataFrame):
    """재료를 카드 형태로 표시"""
    num_cols = 3  # 한 줄에 3개씩 표시
    rows = [df.iloc[i:i + num_cols] for i in range(0, len(df), num_cols)]

    for row_data in rows:
        cols = st.columns(num_cols)
        for i, (idx, ingredient) in enumerate(row_data.iterrows()):
            with cols[i]:
                # 유통기한 임박 색상 설정
                card_color = "#f0f2f6"  # 기본 배경색
                text_color = "#333333" # 기본 글자색
                today = datetime.now().date()
                if pd.notna(ingredient['expiry_date']):
                    expiry_date_obj = pd.to_datetime(ingredient['expiry_date']).date()
                    if today <= expiry_date_obj <= today + timedelta(days=3):
                        card_color = "#fff3cd" # 유통기한 임박 (연한 노랑)
                        text_color = "#856404" # 진한 노랑
                    elif expiry_date_obj < today:
                        card_color = "#f8d7da" # 유통기한 지남 (연한 빨강)
                        text_color = "#721c24" # 진한 빨강

                st.markdown(f"""
                    <div style="
                        background-color: {card_color};
                        border-radius: 10px;
                        padding: 15px;
                        margin-bottom: 10px;
                        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
                        height: 100%;
                        display: flex;
                        flex-direction: column;
                        justify-content: space-between;
                        color: {text_color};
                    ">
                        <h4 style="margin-top: 0; margin-bottom: 10px; color: {text_color};">{ingredient['name']}</h4>
                        <p style="margin: 0; font-size: 0.9em;"><strong>카테고리:</strong> {ingredient['category']}</p>
                        <p style="margin: 0; font-size: 0.9em;"><strong>수량:</strong> {ingredient['quantity']} {ingredient['unit']}</p>
                        <p style="margin: 0; font-size: 0.9em;"><strong>유통기한:</strong> {ingredient['expiry_date'].strftime('%Y-%m-%d') if pd.notna(ingredient['expiry_date']) else '정보 없음'}</p>
                    </div>
                """, unsafe_allow_html=True)

def show_recipe_recommendation(db: DatabaseManager):
    """레시피 추천 페이지"""
    st.header("🍳 레시피 추천")
    
    st.markdown("현재 가지고 있는 재료들을 기반으로 새로운 레시피를 추천받아보세요!")
    
    ingredients_df = db.get_ingredients()
    
    if ingredients_df.empty:
        st.warning("냉장고에 재료가 없습니다. '재료 관리' 탭에서 재료를 추가해주세요.")
        return
        
    available_ingredients = ingredients_df['name'].tolist()
    
    st.write("---")
    st.subheader("🤖 AI 레시피 추천")
    
    selected_ingredients = st.multiselect(
        "레시피에 사용할 재료를 선택하세요:",
        options=available_ingredients,
        default=available_ingredients[:5] if len(available_ingredients) >= 5 else available_ingredients
    )
    
    user_preferences = st.text_area("추가적인 요청사항 (예: 매콤하게, 간단한 요리, 아이들을 위한 요리 등)")
    
    if st.button("레시피 추천받기"):
        if not selected_ingredients:
            st.warning("적어도 하나 이상의 재료를 선택해주세요.")
            return
        
        with st.spinner("AI가 맛있는 레시피를 추천 중입니다..."):
            recipe_gen = RecipeGenerator()
            recommended_recipe = recipe_gen.generate_recipe_from_ingredients(selected_ingredients, user_preferences)
            
            if recommended_recipe:
                st.success("레시피가 생성되었습니다!")
                
                # 레시피 정보 표시
                st.subheader(f"✨ {recommended_recipe.get('name', '새로운 레시피')}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("조리 시간", f"{recommended_recipe.get('cooking_time', 'N/A')}분")
                with col2:
                    st.metric("인분", f"{recommended_recipe.get('servings', 'N/A')}인분")
                with col3:
                    st.metric("난이도", recommended_recipe.get('difficulty', 'N/A'))
                
                st.markdown("---")
                st.subheader("재료")
                for ingredient in recommended_recipe.get('ingredients', []):
                    st.write(f"- {ingredient.get('name', 'N/A')}: {ingredient.get('quantity', 'N/A')} {ingredient.get('unit', '')}")
                    
                st.subheader("조리법")
                instructions = recommended_recipe.get('instructions', '조리법이 없습니다.')
                # 줄 바꿈 문자를 기준으로 분리하여 목록으로 표시
                instruction_steps = instructions.split('\n')
                for step in instruction_steps:
                    if step.strip(): # 빈 줄 제외
                        st.write(f"• {step.strip()}")
                
                if recommended_recipe.get('tips'):
                    st.subheader("셰프의 팁")
                    st.info(recommended_recipe['tips'])
                
                # 레시피 저장 버튼
                if st.button("이 레시피 저장하기"):
                    try:
                        db.add_recipe(
                            name=recommended_recipe.get('name', '이름 없음'),
                            ingredients=recommended_recipe.get('ingredients', []),
                            instructions=recommended_recipe.get('instructions', ''),
                            cooking_time=recommended_recipe.get('cooking_time', 0),
                            servings=recommended_recipe.get('servings', 0),
                            category=recommended_recipe.get('category', '기타'),
                            difficulty=recommended_recipe.get('difficulty', '쉬움')
                        )
                        st.success("레시피가 성공적으로 저장되었습니다!")
                    except Exception as e:
                        st.error(f"레시피 저장 중 오류 발생: {str(e)}")
            else:
                st.warning("죄송합니다. 선택하신 재료로 레시피를 생성할 수 없습니다. 다른 재료를 선택하거나 요청사항을 변경해보세요.")

def show_recipe_book(db: DatabaseManager):
    """레시피 북 페이지"""
    st.header("📖 레시피 북")
    
    # 탭 구조로 변경
    tab1, tab2 = st.tabs(["📖 저장된 레시피", "🔍 AI 레시피 검색"])
    
    with tab1:
        recipes_df = db.get_recipes()
        
        if recipes_df.empty:
            st.info("아직 저장된 레시피가 없습니다. '레시피 추천' 탭에서 레시피를 추가해보세요!")
            return
            
        # 레시피 검색 및 필터링
        search_query = st.text_input("레시피 검색 (이름, 재료, 카테고리 등)")
        
        # 카테고리 필터
        categories = ["전체"] + list(recipes_df['category'].unique())
        selected_category = st.selectbox("카테고리별 필터", categories)
        
        # 난이도 필터
        difficulties = ["전체"] + list(recipes_df['difficulty'].unique())
        selected_difficulty = st.selectbox("난이도별 필터", difficulties)
        
        filtered_recipes = recipes_df.copy()
        
        if search_query:
            filtered_recipes = filtered_recipes[
                filtered_recipes['name'].str.contains(search_query, case=False, na=False) |
                filtered_recipes['ingredients'].str.contains(search_query, case=False, na=False) |
                filtered_recipes['instructions'].str.contains(search_query, case=False, na=False) |
                filtered_recipes['category'].str.contains(search_query, case=False, na=False)
            ]
            
        if selected_category != "전체":
            filtered_recipes = filtered_recipes[filtered_recipes['category'] == selected_category]
            
        if selected_difficulty != "전체":
            filtered_recipes = filtered_recipes[filtered_recipes['difficulty'] == selected_difficulty]
        
    if filtered_recipes.empty:
        st.info("검색 조건에 맞는 레시피가 없습니다.")
        return
        
    # 레시피 목록 표시
    st.subheader("나의 레시피 목록")
    
    # 레시피 정렬 옵션
    sort_option = st.selectbox("정렬 기준", ["최근 추가된 순", "많이 사용된 순", "이름 순"])
    
    if sort_option == "최근 추가된 순":
        filtered_recipes = filtered_recipes.sort_values(by='created_at', ascending=False)
    elif sort_option == "많이 사용된 순":
        filtered_recipes = filtered_recipes.sort_values(by='used_count', ascending=False)
    elif sort_option == "이름 순":
        filtered_recipes = filtered_recipes.sort_values(by='name', ascending=True)

    for _, recipe in filtered_recipes.iterrows():
        with st.expander(f"**{recipe['name']}** ({recipe['category']} / {recipe['difficulty']}) - 사용 횟수: {recipe['used_count']}회"):
            st.write(f"**조리 시간:** {recipe['cooking_time']}분")
            st.write(f"**인분:** {recipe['servings']}인분")
            
            st.markdown("#### 필요한 재료:")
            try:
                # JSON 문자열을 파싱
                recipe_ingredients = json.loads(recipe['ingredients'])
                for ing in recipe_ingredients:
                    st.write(f"- {ing.get('name', 'N/A')}: {ing.get('quantity', 'N/A')} {ing.get('unit', '')}")
            except json.JSONDecodeError:
                st.write("재료 정보를 불러올 수 없습니다.")
                
            st.markdown("#### 조리법:")
            instructions = recipe['instructions']
            for step in instructions.split('\n'):
                if step.strip():
                    st.write(f"• {step.strip()}")
            
            # 사용횟수가 1 이상인 경우 요리기록 탭 추가
            if recipe['used_count'] >= 1:
                st.markdown("#### 📝 요리 기록")
                # 해당 레시피의 요리 기록 조회
                conn = db._get_conn()
                history_df = pd.read_sql_query('''
                    SELECT * FROM cooking_history 
                    WHERE recipe_id = ?
                    ORDER BY cooking_date DESC
                ''', conn, params=(recipe['id'],))
                conn.close()
                
                if not history_df.empty:
                    for _, record in history_df.iterrows():
                        st.write(f"🗓️ {record['cooking_date']} - ⭐{record['rating']} - {record['notes'] if record['notes'] else '메모 없음'}")
                else:
                    st.write("아직 요리 기록이 없습니다.")
            
            col_use, col_delete = st.columns(2)
            with col_use:
                if st.button(f"'{recipe['name']}' 요리했어요!", key=f"use_recipe_{recipe['id']}"):
                    # 레시피 사용 횟수 증가
                    db.update_recipe_usage(recipe['id'])
                    st.success(f"'{recipe['name']}' 요리 기록이 업데이트되었습니다.")
                    st.rerun()
            with col_delete:
                if st.button(f"'{recipe['name']}' 레시피 삭제", key=f"delete_recipe_{recipe['id']}"):
                    db.delete_recipe(recipe['id'])
                    st.success(f"'{recipe['name']}' 레시피가 삭제되었습니다.")
                    st.rerun()
    
    with tab2:
        st.subheader("🔍 AI 레시피 검색")
        
        st.write("OpenAI를 활용하여 새로운 레시피를 검색하고 저장할 수 있습니다.")
        
        # 검색 옵션
        col1, col2 = st.columns(2)
        with col1:
            search_query = st.text_input("요리명 또는 재료로 검색", placeholder="예: 김치찌개, 닭가슴살 요리")
            cuisine_type = st.selectbox("요리 종류", ["한식", "중식", "일식", "양식", "기타"])
        
        with col2:
            difficulty = st.selectbox("난이도", ["쉬움", "보통", "어려움"])
            cooking_time = st.selectbox("조리 시간", ["30분 이내", "1시간 이내", "1시간 이상"])
        
        if st.button("🔍 AI 레시피 검색") and search_query:
            with st.spinner("AI가 레시피를 검색하는 중..."):
                try:
                    recipe_gen = RecipeGenerator()
                    
                    # AI 검색 프롬프트 생성
                    search_prompt = f"""
                    다음 조건에 맞는 {cuisine_type} 레시피를 추천해주세요:
                    - 검색어: {search_query}
                    - 난이도: {difficulty}
                    - 조리시간: {cooking_time}
                    
                    다음 JSON 형식으로 응답해주세요:
                    {{
                        "name": "요리 이름",
                        "ingredients": [
                            {{"name": "재료명", "quantity": "분량", "unit": "단위"}},
                            ...
                        ],
                        "instructions": "조리법 (단계별로 설명)",
                        "cooking_time": 조리시간(분),
                        "servings": 몇인분,
                        "category": "{cuisine_type}",
                        "difficulty": "{difficulty}",
                        "tips": "조리 팁"
                    }}
                    """
                    
                    # OpenAI API 호출
                    response = recipe_gen.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "당신은 전문 요리사입니다. 사용자의 요청에 맞는 맛있는 레시피를 추천해주세요."},
                            {"role": "user", "content": search_prompt}
                        ],
                        temperature=0.7
                    )
                    
                    recipe_text = response.choices[0].message.content
                    # JSON 부분만 추출
                    json_match = re.search(r'\{.*\}', recipe_text, re.DOTALL)
                    if json_match:
                        recipe_data = json.loads(json_match.group())
                        
                        st.success("레시피를 찾았습니다!")
                        
                        # 레시피 표시
                        st.subheader(f"🍳 {recipe_data['name']}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("조리시간", f"{recipe_data['cooking_time']}분")
                        with col2:
                            st.metric("인분", f"{recipe_data['servings']}인분")
                        with col3:
                            st.metric("난이도", recipe_data['difficulty'])
                        
                        st.write(f"**카테고리:** {recipe_data['category']}")
                        
                        # 재료
                        st.subheader("📝 재료")
                        for ingredient in recipe_data['ingredients']:
                            st.write(f"• {ingredient['name']}: {ingredient['quantity']} {ingredient['unit']}")
                        
                        # 조리법
                        st.subheader("👨‍🍳 조리법")
                        st.write(recipe_data['instructions'])
                        
                        # 팁
                        if 'tips' in recipe_data:
                            st.subheader("💡 조리 팁")
                            st.write(recipe_data['tips'])
                        
                        # 레시피 저장
                        if st.button("📖 이 레시피 저장하기", key="save_searched_recipe"):
                            try:
                                db.add_recipe(
                                    name=recipe_data['name'],
                                    ingredients=recipe_data['ingredients'],
                                    instructions=recipe_data['instructions'],
                                    cooking_time=recipe_data['cooking_time'],
                                    servings=recipe_data['servings'],
                                    category=recipe_data['category'],
                                    difficulty=recipe_data['difficulty']
                                )
                                st.success("레시피가 저장되었습니다!")
                                # 캐시 클리어 및 페이지 새로고침
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"레시피 저장 중 오류 발생: {str(e)}")
                    else:
                        st.error("레시피 형식을 파싱할 수 없습니다.")
                        
                except Exception as e:
                    st.error(f"레시피 검색 중 오류 발생: {str(e)}")
                    st.info("OpenAI API 키가 설정되지 않았거나 오류가 발생했습니다. .env 파일에 OPENAI_API_KEY를 설정해주세요.")

def show_shopping_list(db: DatabaseManager):
    """쇼핑 리스트 페이지"""
    st.header("🛒 쇼핑 리스트")
    
    st.subheader("새로운 쇼핑 품목 추가")
    with st.form("add_shopping_item"):
        col1, col2 = st.columns(2)
        with col1:
            item_name = st.text_input("품목명")
        with col2:
            item_quantity = st.number_input("수량", min_value=0.1, step=0.1)
            item_unit = st.selectbox("단위", ["개", "g", "kg", "ml", "L", "컵", "큰술", "작은술"])
        item_priority = st.slider("우선순위", 1, 5, 3) # 1: 낮음, 5: 높음
        
        submitted = st.form_submit_button("쇼핑 품목 추가")
        if submitted and item_name:
            db.add_to_shopping_list(item_name, item_quantity, item_unit, item_priority)
            st.success(f"'{item_name}'이 쇼핑 리스트에 추가되었습니다.")
            st.rerun()
            
    st.subheader("나의 쇼핑 리스트")
    shopping_df = db.get_shopping_list()
    
    if shopping_df.empty:
        st.info("쇼핑 리스트가 비어 있습니다.")
    else:
        # 우선순위에 따라 정렬하여 표시
        shopping_df['priority_str'] = shopping_df['priority'].map({
            1: '낮음', 2: '보통', 3: '중간', 4: '높음', 5: '매우 높음'
        })
        
        # 'purchased' 컬럼은 체크박스를 위해 제외
        display_df = shopping_df[['id', 'ingredient_name', 'quantity', 'unit', 'priority_str', 'created_at']].copy()
        display_df.columns = ['ID', '품목명', '수량', '단위', '우선순위', '추가일']
        
        st.dataframe(display_df, hide_index=True)
        
        st.write("---")
        st.subheader("구매 완료 처리")
        
        # 구매 완료 처리할 품목 선택 (멀티셀렉트)
        items_to_mark_purchased = st.multiselect(
            "구매 완료한 품목을 선택하세요 (ID 기준):",
            options=shopping_df['id'].tolist(),
            format_func=lambda x: f"{shopping_df[shopping_df['id'] == x]['ingredient_name'].iloc[0]} (ID: {x})"
        )
        
        if st.button("선택한 품목 구매 완료로 표시"):
            if items_to_mark_purchased:
                for item_id in items_to_mark_purchased:
                    db.update_shopping_item_status(item_id, True)
                st.success("선택된 품목들이 구매 완료 처리되었습니다.")
                st.rerun()
            else:
                st.warning("구매 완료할 품목을 선택해주세요.")
    
    # 구매 완료된 재료들을 날짜별로 표시
    st.write("---")
    st.subheader("📋 구매 완료 내역")
    
    # 구매 완료된 항목 조회
    conn = db._get_conn()
    purchased_df = pd.read_sql_query('''
        SELECT ingredient_name, quantity, unit, priority, created_at
        FROM shopping_list 
        WHERE purchased = TRUE
        ORDER BY created_at DESC
    ''', conn)
    conn.close()
    
    if not purchased_df.empty:
        # 날짜별로 그룹화
        purchased_df['created_at'] = pd.to_datetime(purchased_df['created_at'])
        purchased_df['date'] = purchased_df['created_at'].dt.date
        
        # 우선순위 문자열 변환
        purchased_df['priority_str'] = purchased_df['priority'].map({
            1: '낮음', 2: '보통', 3: '중간', 4: '높음', 5: '매우 높음'
        })
        
        # 날짜별로 표시
        for date in purchased_df['date'].unique():
            date_items = purchased_df[purchased_df['date'] == date]
            with st.expander(f"📅 {date} ({len(date_items)}개 품목)"):
                display_cols = ['ingredient_name', 'quantity', 'unit', 'priority_str']
                display_df = date_items[display_cols].copy()
                display_df.columns = ['품목명', '수량', '단위', '우선순위']
                st.dataframe(display_df, hide_index=True)
    else:
        st.info("구매 완료된 품목이 없습니다.")

def show_cooking_history(db: DatabaseManager):
    """요리 기록 페이지"""
    st.header("📝 요리 기록")
    
    # 탭 구조로 변경
    tab1, tab2, tab3 = st.tabs(["📝 직접 입력", "📖 레시피에서 가져오기", "📋 기록 목록"])
    
    with tab1:
        st.subheader("📝 요리 기록 직접 입력")
        
        with st.form("add_cooking_record"):
            col1, col2 = st.columns(2)
            
            with col1:
                recipe_name = st.text_input("요리명")
                cooking_date = st.date_input("요리한 날짜", value=datetime.now().date())
                rating = st.selectbox("평점", [1, 2, 3, 4, 5], index=4, format_func=lambda x: "⭐" * x)
            
            with col2:
                ingredients_used = st.text_area("사용한 재료", placeholder="예: 달걀 2개, 양파 1개, 소금 약간")
                cooking_time = st.number_input("조리 시간 (분)", min_value=1, value=30)
                servings = st.number_input("인분", min_value=1, value=2)
            
            notes = st.text_area("메모 및 후기", placeholder="맛, 개선점, 다음에 시도할 것 등을 기록하세요")
            
            if st.form_submit_button("기록 저장"):
                if recipe_name:
                    # 요리 기록을 데이터베이스에 저장
                    conn = db._get_conn()
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO cooking_history (recipe_id, ingredients_used, cooking_date, rating, notes)
                        VALUES (NULL, ?, ?, ?, ?)
                    ''', (f"{recipe_name}|{ingredients_used}|{cooking_time}분|{servings}인분", cooking_date, rating, notes))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"{recipe_name} 요리 기록이 저장되었습니다!")
                    st.rerun()
    
    with tab2:
        st.subheader("📖 저장된 레시피에서 가져오기")
        
        recipes_df = db.get_recipes()
        
        if not recipes_df.empty:
            selected_recipe = st.selectbox(
                "레시피 선택",
                options=recipes_df['id'].tolist(),
                format_func=lambda x: recipes_df[recipes_df['id'] == x]['name'].iloc[0]
            )
            
            if selected_recipe:
                recipe = recipes_df[recipes_df['id'] == selected_recipe].iloc[0]
                
                st.write(f"**선택된 레시피:** {recipe['name']}")
                st.write(f"**카테고리:** {recipe['category']}")
                st.write(f"**난이도:** {recipe['difficulty']}")
                st.write(f"**조리시간:** {recipe['cooking_time']}분")
                
                with st.form("add_recipe_cooking_record"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        cooking_date = st.date_input("요리한 날짜", value=datetime.now().date())
                        rating = st.selectbox("평점", [1, 2, 3, 4, 5], index=4, format_func=lambda x: "⭐" * x)
                    
                    with col2:
                        actual_servings = st.number_input("실제 만든 인분", min_value=1, value=recipe['servings'])
                        difficulty_felt = st.selectbox("체감 난이도", ["쉬움", "보통", "어려움"], index=["쉬움", "보통", "어려움"].index(recipe['difficulty']))
                    
                    # 재료 사용 확인
                    try:
                        ingredients = json.loads(recipe['ingredients'])
                        st.write("**사용한 재료 확인:**")
                        ingredients_used_list = []
                        for ingredient in ingredients:
                            used = st.checkbox(f"{ingredient['name']}: {ingredient['quantity']} {ingredient['unit']}", value=True)
                            if used:
                                ingredients_used_list.append(f"{ingredient['name']} {ingredient['quantity']} {ingredient['unit']}")
                    except:
                        ingredients_used_list = ["재료 정보 없음"]
                    
                    notes = st.text_area("메모 및 후기", placeholder="맛, 개선점, 다음에 시도할 것 등을 기록하세요")
                    
                    if st.form_submit_button("기록 저장"):
                        # 요리 기록을 데이터베이스에 저장
                        try:
                            conn = db._get_conn()
                            cursor = conn.cursor()
                            
                            ingredients_used_str = ", ".join(ingredients_used_list)
                            
                            cursor.execute('''
                                INSERT INTO cooking_history (recipe_id, ingredients_used, cooking_date, rating, notes)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (selected_recipe, ingredients_used_str, cooking_date, rating, notes))
                            
                            # 레시피 사용 횟수 업데이트 (같은 연결 사용)
                            cursor.execute('UPDATE recipes SET used_count = used_count + 1 WHERE id = ?', (selected_recipe,))
                            
                            conn.commit()
                        except Exception as e:
                            st.error(f"데이터베이스 오류: {str(e)}")
                        finally:
                            if conn:
                                conn.close()
                        
                        st.success(f"{recipe['name']} 요리 기록이 저장되었습니다!")
                        st.rerun()
        else:
            st.info("저장된 레시피가 없습니다. 레시피를 먼저 저장해주세요.")
    
    with tab3:
        st.subheader("📋 요리 기록 목록")
        
        # 요리 기록 조회
        conn = db._get_conn()
        history_df = pd.read_sql_query('''
            SELECT ch.*, r.name as recipe_name 
            FROM cooking_history ch
            LEFT JOIN recipes r ON ch.recipe_id = r.id
            ORDER BY ch.cooking_date DESC
        ''', conn)
        conn.close()
        
        if not history_df.empty:
            for _, record in history_df.iterrows():
                with st.expander(f"{record['recipe_name'] if pd.notna(record['recipe_name']) else '직접 입력'} - {record['cooking_date']} (⭐{record['rating']})"):
                    st.write(f"**요리한 날짜:** {record['cooking_date']}")
                    st.write(f"**평점:** {'⭐' * record['rating']}")
                    st.write(f"**사용한 재료:** {record['ingredients_used']}")
                    if record['notes']:
                        st.write(f"**메모:** {record['notes']}")
                    
                    # 삭제 버튼
                    if st.button(f"기록 삭제", key=f"delete_history_{record['id']}"):
                        conn = db._get_conn()
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM cooking_history WHERE id = ?', (record['id'],))
                        conn.commit()
                        conn.close()
                        st.success("기록이 삭제되었습니다!")
                        st.rerun()
        else:
            st.info("요리 기록이 없습니다. 요리를 하고 기록을 남겨보세요!")

def show_analytics_dashboard(db: DatabaseManager):
    """분석 대시보드 페이지"""
    st.header("📊 분석 대시보드")
    
    ingredients_df = db.get_ingredients()
    recipes_df = db.get_recipes()
    
    if ingredients_df.empty and recipes_df.empty:
        st.info("아직 데이터가 충분하지 않습니다. 재료를 추가하고 레시피를 저장하여 분석을 시작하세요!")
        return

    st.subheader("재료 카테고리 분포")
    if not ingredients_df.empty:
        category_counts = ingredients_df['category'].value_counts().reset_index()
        category_counts.columns = ['Category', 'Count']
        fig = px.pie(category_counts, values='Count', names='Category', title='보유 재료 카테고리별 분포')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("보유 재료 데이터가 없습니다.")

    st.subheader("가장 많이 사용된 레시피 TOP 5")
    if not recipes_df.empty:
        top_recipes = recipes_df.sort_values(by='used_count', ascending=False).head(5)
        if not top_recipes.empty:
            fig = px.bar(top_recipes, x='name', y='used_count', title='가장 많이 사용된 레시피',
                         labels={'name': '레시피 이름', 'used_count': '사용 횟수'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("사용된 레시피 데이터가 없습니다.")
    else:
        st.info("저장된 레시피 데이터가 없습니다.")
    
    # 쇼핑 리스트 구매완료 분석
    st.subheader("🛒 쇼핑 리스트 구매완료 분석")
    conn = db._get_conn()
    
    # 전체 쇼핑 리스트 통계
    total_items = pd.read_sql_query('SELECT COUNT(*) as count FROM shopping_list', conn).iloc[0]['count']
    purchased_items = pd.read_sql_query('SELECT COUNT(*) as count FROM shopping_list WHERE purchased = TRUE', conn).iloc[0]['count']
    pending_items = total_items - purchased_items
    
    if total_items > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("전체 품목", total_items)
        with col2:
            st.metric("구매완료", purchased_items)
        with col3:
            st.metric("구매대기", pending_items)
        
        # 구매완료율 파이 차트
        if total_items > 0:
            completion_data = pd.DataFrame({
                '상태': ['구매완료', '구매대기'],
                '개수': [purchased_items, pending_items]
            })
            fig = px.pie(completion_data, values='개수', names='상태', 
                        title='쇼핑 리스트 구매완료율',
                        color_discrete_map={'구매완료': '#28a745', '구매대기': '#ffc107'})
            st.plotly_chart(fig, use_container_width=True)
        

    else:
        st.info("쇼핑 리스트 데이터가 없습니다.")
    
    # 사용율이 높은 식재료 분석
    st.subheader("📈 사용율이 높은 식재료 TOP 10")
    
    # 레시피에서 사용된 재료들을 분석
    ingredient_usage = {}
    
    if not recipes_df.empty:
        for _, recipe in recipes_df.iterrows():
            try:
                ingredients = json.loads(recipe['ingredients'])
                usage_count = recipe['used_count']
                
                for ingredient in ingredients:
                    ingredient_name = ingredient.get('name', '').lower()
                    if ingredient_name:
                        if ingredient_name in ingredient_usage:
                            ingredient_usage[ingredient_name] += usage_count
                        else:
                            ingredient_usage[ingredient_name] = usage_count
            except:
                continue
        
        if ingredient_usage:
            # 상위 10개 재료
            top_ingredients = sorted(ingredient_usage.items(), key=lambda x: x[1], reverse=True)[:10]
            
            if top_ingredients:
                ingredient_df = pd.DataFrame(top_ingredients, columns=['재료명', '사용횟수'])
                
                fig = px.bar(ingredient_df, x='재료명', y='사용횟수', 
                           title='가장 많이 사용된 식재료 TOP 10',
                           labels={'재료명': '재료명', '사용횟수': '총 사용횟수'})
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
                
                # 테이블로도 표시
                st.dataframe(ingredient_df, hide_index=True)
            else:
                st.info("사용된 재료 데이터가 없습니다.")
        else:
            st.info("레시피 사용 데이터가 없습니다.")
    else:
        st.info("레시피 데이터가 없습니다.")
    
    conn.close()

if __name__ == "__main__":
    main()