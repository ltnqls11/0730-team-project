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
# openai.api_key = st.secrets["OPENAI_API_KEY"]  # Streamlit secrets 사용

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                repurchase_cycle INTEGER DEFAULT 7,  -- 재구매 주기 (일)
                last_purchase_date DATE,
                is_frequent_item BOOLEAN DEFAULT FALSE,  -- 자주 구매하는 재료인지
                auto_repurchase_alert BOOLEAN DEFAULT TRUE  -- 자동 재구매 알림 여부
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
                used_count INTEGER DEFAULT 0,
                calories REAL DEFAULT 0,  -- 칼로리 (kcal)
                carbs REAL DEFAULT 0,     -- 탄수화물 (g)
                protein REAL DEFAULT 0,   -- 단백질 (g)
                fat REAL DEFAULT 0        -- 지방 (g)
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
                calories_consumed REAL DEFAULT 0,  -- 섭취한 칼로리
                carbs_consumed REAL DEFAULT 0,     -- 섭취한 탄수화물
                protein_consumed REAL DEFAULT 0,   -- 섭취한 단백질
                fat_consumed REAL DEFAULT 0,       -- 섭취한 지방
                servings_consumed REAL DEFAULT 1,  -- 섭취한 인분
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
        
        # 재구매 기록 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS repurchase_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_name TEXT NOT NULL,
                purchase_date DATE DEFAULT (date('now')),
                quantity REAL,
                unit TEXT,
                price REAL,
                store TEXT,
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
                   cooking_time: int, servings: int, category: str, difficulty: str,
                   calories: float = 0, carbs: float = 0, protein: float = 0, fat: float = 0):
        """레시피 추가"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        ingredients_json = json.dumps(ingredients, ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO recipes (name, ingredients, instructions, cooking_time, servings, category, difficulty, calories, carbs, protein, fat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, ingredients_json, instructions, cooking_time, servings, category, difficulty, calories, carbs, protein, fat))
        
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
    
    def add_cooking_history(self, recipe_id: int, rating: int = None, notes: str = None, ingredients_used: str = None):
        """요리 기록 추가"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO cooking_history (recipe_id, rating, notes, ingredients_used)
            VALUES (?, ?, ?, ?)
        ''', (recipe_id, rating, notes, ingredients_used))
        
        # 레시피 사용 횟수도 함께 증가
        cursor.execute('UPDATE recipes SET used_count = used_count + 1 WHERE id = ?', (recipe_id,))
        
        conn.commit()
        conn.close()
        return True

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
    
    def delete_shopping_item(self, item_id: int):
        """쇼핑리스트에서 특정 항목 삭제"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM shopping_list WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()

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
            "tips": "조리 팁",
            "nutrition": {{
                "calories": 1인분당_칼로리(kcal),
                "carbs": 1인분당_탄수화물(g),
                "protein": 1인분당_단백질(g),
                "fat": 1인분당_지방(g)
            }}
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
        page_title="스마트 키친 - 오늘 뭐 먹지?",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # 파스텔 톤 기반 UI 디자인 스타일 가이드 적용
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
    
    :root {
        /* 메인 컬러 - 연한 보라색 계열 (세련된 느낌) */
        --primary-color: #D4B8E3;
        --primary-light: #E6B8E3;
        --primary-dark: #C2B8E3;
        
        /* 보조 컬러 - 크림, 연한 그레이 (배경) */
        --secondary-color: #F5F5DC;
        --secondary-light: #FAFAF0;
        --secondary-dark: #E8E8D0;
        
        /* 포인트 컬러 - 연한 보라색 중심 파스텔 톤 */
        --accent-orange: #F4C2C2;
        --accent-red: #FF9B9B;
        --accent-yellow: #FFE5B4;
        --accent-blue: #B8D4E3;
        --accent-purple: #D4B8E3;
        --accent-pink: #F0B8E3;
        
        /* 배경 및 텍스트 */
        --bg-primary: #FEFEFE;
        --bg-secondary: #F8F9FA;
        --bg-card: #FFFFFF;
        --text-primary: #2C3E50;
        --text-secondary: #6C757D;
        --text-light: #ADB5BD;
        
        /* 경계선 */
        --border-light: #E9ECEF;
        --border-medium: #DEE2E6;
        
        /* 상태 컬러 (연한 보라색 중심 파스텔 톤) */
        --success-light: #E6B8E3;
        --success-dark: #D4B8E3;
        --warning-light: #F4C2C2;
        --warning-dark: #FF9B9B;
        --error-light: #FF9B9B;
        --error-dark: #F4C2C2;
        --info-light: #B8D4E3;
        --info-dark: #D4B8E3;
    }
    
    * {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    .main {
        padding-top: 1rem;
        background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
        min-height: 100vh;
    }
    
    /* 탭 스타일링 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: var(--bg-card);
        padding: 12px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(212, 184, 227, 0.1);
        border: 1px solid var(--border-light);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        padding: 0 24px;
        background: transparent;
        border-radius: 12px;
        border: none;
        color: var(--text-secondary);
        font-weight: 500;
        font-size: 14px;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(212, 184, 227, 0.3);
        transform: translateY(-1px);
    }
    
    /* 카드 스타일링 */
    .metric-card {
        background: var(--bg-card);
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid var(--border-light);
        text-align: center;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    
    .feature-card {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 8px 25px rgba(212, 184, 227, 0.25);
        transition: all 0.3s ease;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .feature-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(212, 184, 227, 0.35);
    }
    
    .feature-card-accent {
        background: linear-gradient(135deg, var(--accent-orange) 0%, var(--accent-yellow) 100%);
        padding: 2rem;
        border-radius: 20px;
        color: var(--text-primary);
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 8px 25px rgba(244, 194, 194, 0.25);
        transition: all 0.3s ease;
    }
    
    .feature-card-warning {
        background: linear-gradient(135deg, var(--accent-red) 0%, var(--accent-pink) 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 8px 25px rgba(255, 155, 155, 0.25);
        transition: all 0.3s ease;
    }
    
    .recipe-card {
        background: var(--bg-card);
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border-left: 4px solid var(--primary-color);
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .recipe-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    
    .nutrition-card {
        background: linear-gradient(135deg, var(--success-light) 0%, var(--success-dark) 100%);
        padding: 1rem;
        border-radius: 12px;
        color: var(--text-primary);
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(212, 184, 227, 0.2);
    }
    
    .warning-card {
        background: linear-gradient(135deg, var(--warning-light) 0%, var(--warning-dark) 100%);
        padding: 1rem;
        border-radius: 12px;
        color: var(--text-primary);
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(244, 194, 194, 0.2);
    }
    
    .success-card {
        background: linear-gradient(135deg, var(--info-light) 0%, var(--info-dark) 100%);
        padding: 1rem;
        border-radius: 12px;
        color: var(--text-primary);
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(212, 184, 227, 0.2);
    }
    
    /* 버튼 스타일링 */
    .stButton > button {
        border-radius: 12px;
        border: none;
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
        color: white;
        font-weight: 500;
        font-size: 14px;
        padding: 8px 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(212, 184, 227, 0.25);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(212, 184, 227, 0.35);
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-color) 100%);
    }
    
    /* 입력 필드 스타일링 */
    .stSelectbox > div > div {
        border-radius: 12px;
        border: 2px solid var(--border-light);
        background: var(--bg-card);
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:hover {
        border-color: var(--primary-light);
        box-shadow: 0 2px 10px rgba(212, 184, 227, 0.1);
    }
    
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid var(--border-light);
        background: var(--bg-card);
        padding: 12px 16px;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(212, 184, 227, 0.1);
    }
    
    .stTextArea > div > div > textarea {
        border-radius: 12px;
        border: 2px solid var(--border-light);
        background: var(--bg-card);
        padding: 12px 16px;
        transition: all 0.3s ease;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(212, 184, 227, 0.1);
    }
    
    /* 체크박스 스타일링 */
    .stCheckbox > div > div {
        border-radius: 8px;
        border: 2px solid var(--border-light);
        background: var(--bg-card);
        transition: all 0.3s ease;
    }
    
    .stCheckbox > div > div:hover {
        border-color: var(--primary-light);
    }
    
    /* 메트릭 스타일링 */
    .stMetric {
        background: var(--bg-card);
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid var(--border-light);
        transition: all 0.3s ease;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    
    /* 헤더 스타일링 */
    h1 {
        color: var(--text-primary);
        font-weight: 700;
        margin-bottom: 2rem;
        font-size: 2.5rem;
        # background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
        -webkit-background-clip: text;
        # -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    h2 {
        color: var(--text-primary);
        font-weight: 600;
        margin-bottom: 1rem;
        font-size: 1.8rem;
    }
    
    h3 {
        color: var(--text-primary);
        font-weight: 500;
        margin-bottom: 0.8rem;
        font-size: 1.4rem;
    }
    
    /* 데이터프레임 스타일링 */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    
    /* 차트 컨테이너 스타일링 */
    .js-plotly-plot {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        background: var(--bg-card);
        padding: 1rem;
    }
    
    /* 스크롤바 스타일링 */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary-light);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-color);
    }
    
    /* 애니메이션 */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stApp > div > div > div > div > section > div {
        animation: fadeIn 0.5s ease-out;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 파스텔 톤 기반 헤더
    # st.markdown("""
    # <div style="text-align: center; padding: 3rem 0;background: linear-gradient(135deg, #D4B8E3 0%, #D4B8E3 50%, #D4B8E3 100%); border-radius: 20px; margin-bottom: 2rem; box-shadow:none; position: relative; overflow: hidden;">
    #     <div style="position: absolute; top: -50px; left: -50px; width: 100px; height: 100px; background: rgba(255, 255, 255, 0.1); border-radius: 50%;"></div>
    #     <div style="position: absolute; top: -30px; right: -30px; width: 80px; height: 80px; background: rgba(255, 255, 255, 0.1); border-radius: 50%;"></div>
    #     <div style="position: absolute; bottom: -40px; left: 20%; width: 60px; height: 60px; background: rgba(255, 255, 255, 0.1); border-radius: 50%;"></div>
    #     <h1 style="
    #         color: black;
    #         font-size: 3rem;
    #         margin: 0;
    #         font-weight: 700;
    #         position: relative;
    #         z-index: 1;
    #         letter-spacing: 0.03em;
    #     ">🍽️ 오늘 뭐먹지?</h1>
    #     <p style="color: rgba(255,255,255,0.); font-size: 1.2rem; margin: 0.8rem 0 0 0; font-weight: 400; position: relative; z-index: 1;">AI와 함께하는 똑똑한 요리 생활</p>
    #     <div style="margin-top: 1rem; position: relative; z-index: 1;">
    #         <span style="display: inline-block; background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; font-size: 0.9rem; color: black;">🥬 재료 관리</span>
    #         <span style="display: inline-block; background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; font-size: 0.9rem; color: black;">🍳 레시피 추천</span>
    #         <span style="display: inline-block; background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; font-size: 0.9rem; color: black;">📊 분석 대시보드</span>
    #     </div>
    # </div>
    # """, unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; padding: 3rem 0;background: linear-gradient(135deg, #D4B8E3 0%, #D4B8E3 50%, #D4B8E3 100%); border-radius: 20px; margin-bottom: 2rem; box-shadow:none; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; left: -50px; width: 100px; height: 100px; background: rgba(255, 255, 255, 0.1); border-radius: 50%;"></div>
        <div style="position: absolute; top: -30px; right: -30px; width: 80px; height: 80px; background: rgba(255, 255, 255, 0.1); border-radius: 50%;"></div>
        <div style="position: absolute; bottom: -40px; left: 20%; width: 60px; height: 60px; background: rgba(255, 255, 255, 0.1); border-radius: 50%;"></div>
        <h1 style="
            color: black; /* Changed from black to white */
            font-size: 3rem;
            margin: 0;
            font-weight: 700;
            position: relative;
            z-index: 1;
            letter-spacing: 0.03em;
        ">🍽️ 오늘 뭐먹지?</h1>
        <p style="color: black; /* Changed from rgba(255,255,255,0.) to white */ font-size: 1.2rem; margin: 0.8rem 0 0 0; font-weight: 400; position: relative; z-index: 1;">AI와 함께하는 똑똑한 요리 생활</p>
        <div style="margin-top: 1rem; position: relative; z-index: 1;">
            <span style="display: inline-block; background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; font-size: 0.9rem; color: black;">🥬 재료 관리</span>
            <span style="display: inline-block; background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; font-size: 0.9rem; color: black;">🍳 레시피 추천</span>
            <span style="display: inline-block; background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; font-size: 0.9rem; color: black;">📊 분석 대시보드</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 데이터베이스 매니저 초기화
    db = DatabaseManager()
    
    # 메인 탭 메뉴 (사이드바 대신 body에 탭으로 변경)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏠 홈", "🥬 재료 관리", "🍳 레시피 추천", 
        "📖 레시피 북", "🛒 쇼핑 리스트", "📝 요리 기록", "📊 분석 대시보드"
    ])
    
    with tab1:
        show_home_page(db)
    
    with tab2:
        show_ingredient_management(db)
    
    with tab3:
        show_recipe_recommendation(db)
    
    with tab4:
        show_recipe_book(db)
    
    with tab5:
        show_shopping_list(db)
    
    with tab6:
        show_cooking_history(db)
    
    with tab7:
        show_analytics_dashboard(db)

def show_home_page(db: DatabaseManager):
    """홈 페이지"""
    
    # 맛있는 음식 이모지들
    st.markdown("""
    <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #F5F5DC 0%, #FAFAF0 100%); border-radius: 20px; margin: 25px 0; box-shadow: 0 8px 25px rgba(245, 245, 220, 0.3); border: 1px solid rgba(212, 184, 227, 0.2);">
        <h3 style="color: #2C3E50; margin-bottom: 25px; font-weight: 600; font-size: 1.8rem;">🍽️ 다양한 요리 카테고리 🍽️</h3>
        <div style="font-size: 3.5em; line-height: 1.5; margin: 20px 0;">
            🍲 🥘 🍳 🥗 🍜 🍱 🥙 🌮 🍕 🍝 🥞 🧆
        </div>
        <p style="color: #6C757D; margin-top: 20px; font-size: 1.1rem; font-weight: 500;">다양한 요리로 가족의 행복을 만들어보세요!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 통계 정보를 카드 형태로 표시
    st.markdown("### 📊 나의 요리 현황")
    
    ingredients_df = db.get_ingredients()
    recipes_df = db.get_recipes()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #E6B8E3 0%, #D4B8E3 100%); padding: 25px; border-radius: 20px; text-align: center; box-shadow: 0 8px 25px rgba(212, 184, 227, 0.25); border: 1px solid rgba(255,255,255,0.3); transition: all 0.3s ease;">
            <div style="font-size: 3em; margin-bottom: 15px;">🥬</div>
            <h3 style="color: white; margin: 0; font-weight: 600; font-size: 1.2rem;">보유 재료</h3>
            <h2 style="color: white; margin: 8px 0; font-size: 2.5rem; font-weight: 700;">{}</h2>
        </div>
        """.format(len(ingredients_df)), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #B8D4E3 0%, #D4B8E3 100%); padding: 25px; border-radius: 20px; text-align: center; box-shadow: 0 8px 25px rgba(184, 212, 227, 0.25); border: 1px solid rgba(255,255,255,0.3); transition: all 0.3s ease;">
            <div style="font-size: 3em; margin-bottom: 15px;">📖</div>
            <h3 style="color: white; margin: 0; font-weight: 600; font-size: 1.2rem;">저장된 레시피</h3>
            <h2 style="color: white; margin: 8px 0; font-size: 2.5rem; font-weight: 700;">{}</h2>
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
        
        color_gradient = "linear-gradient(135deg, #F4C2C2 0%, #FF9B9B 100%)" if expiring_count > 0 else "linear-gradient(135deg, #E6B8E3 0%, #D4B8E3 100%)"
        box_shadow = "0 8px 25px rgba(244, 194, 194, 0.25)" if expiring_count > 0 else "0 8px 25px rgba(212, 184, 227, 0.25)"
        st.markdown("""
        <div style="background: {}; padding: 25px; border-radius: 20px; text-align: center; box-shadow: {}; border: 1px solid rgba(255,255,255,0.3); transition: all 0.3s ease;">
            <div style="font-size: 3em; margin-bottom: 15px;">⏰</div>
            <h3 style="color: white; margin: 0; font-weight: 600; font-size: 1.2rem;">유통기한 임박</h3>
            <h2 style="color: white; margin: 8px 0; font-size: 2.5rem; font-weight: 700;">{}</h2>
        </div>
        """.format(color_gradient, box_shadow, expiring_count), unsafe_allow_html=True)
    
    # 최근 레시피
    if not recipes_df.empty:
        st.subheader("🔥 인기 레시피 TOP 3")
        top_recipes = recipes_df.head(3)
        for _, recipe in top_recipes.iterrows():
            with st.expander(f"{recipe['name']} (요리한 횟수: {recipe['used_count']}회)"):
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
                
                # 테이블 뷰에서 빠른 삭제 옵션
                st.markdown("---")
                st.markdown("#### 빠른 삭제")
                
                # 재료 선택을 위한 selectbox
                ingredient_options = [(f"{row['name']} ({row['category']}) - {row['quantity']}{row['unit']}", row['id']) 
                                    for _, row in filtered_df.iterrows()]
                
                if ingredient_options:
                    selected_ingredient = st.selectbox(
                        "삭제할 재료 선택:",
                        options=[None] + ingredient_options,
                        format_func=lambda x: "재료를 선택하세요" if x is None else x[0]
                    )
                    
                    if selected_ingredient is not None:
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            if st.button("🗑️ 삭제", key="delete_from_table"):
                                ingredient_name = selected_ingredient[0].split(' (')[0]
                                db.delete_ingredient(selected_ingredient[1])
                                st.success(f"'{ingredient_name}' 재료가 삭제되었습니다.")
                                st.rerun()
                        with col2:
                            st.write(f"선택된 재료: {selected_ingredient[0]}")
            else: # 카드 뷰
                display_ingredients_as_cards(filtered_df)
        else:
            st.info("현재 냉장고에 재료가 없습니다. 새 재료를 추가해주세요!")

    with tab4:
        st.subheader("🗑️ 재료 삭제")
        ingredients_df = db.get_ingredients()
        
        if not ingredients_df.empty:
            st.info("삭제할 재료를 선택하고 '선택한 재료 삭제' 버튼을 클릭하세요.")
            
            # 삭제 방식 선택
            delete_mode = st.radio("삭제 방식 선택", ["개별 선택", "일괄 선택"], horizontal=True)
            
            if delete_mode == "개별 선택":
                # 개별 삭제 - 각 재료마다 삭제 버튼
                st.markdown("### 재료별 개별 삭제")
                
                # 카테고리별 필터
                categories = ["전체"] + list(ingredients_df['category'].unique())
                selected_category = st.selectbox("카테고리 필터", categories, key="delete_category_filter")
                
                if selected_category != "전체":
                    filtered_df = ingredients_df[ingredients_df['category'] == selected_category]
                else:
                    filtered_df = ingredients_df.copy()
                
                # 유통기한으로 정렬
                if 'expiry_date' in filtered_df.columns:
                    filtered_df['expiry_date'] = pd.to_datetime(filtered_df['expiry_date'])
                    filtered_df = filtered_df.sort_values(by='expiry_date')
                
                for _, ingredient in filtered_df.iterrows():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        # 유통기한 상태에 따른 색상 표시
                        today = datetime.now().date()
                        expiry_date = pd.to_datetime(ingredient['expiry_date']).date()
                        
                        if expiry_date < today:
                            status_color = "🔴"
                            status_text = "유통기한 지남"
                        elif expiry_date <= today + timedelta(days=3):
                            status_color = "🟡"
                            status_text = "유통기한 임박"
                        else:
                            status_color = "🟢"
                            status_text = "신선함"
                        
                        st.write(f"{status_color} **{ingredient['name']}** ({ingredient['category']}) - {ingredient['quantity']}{ingredient['unit']} - {expiry_date} ({status_text})")
                    
                    with col2:
                        if st.button(f"삭제", key=f"delete_individual_{ingredient['id']}"):
                            db.delete_ingredient(ingredient['id'])
                            st.success(f"'{ingredient['name']}' 재료가 삭제되었습니다.")
                            st.rerun()
            
            else:  # 일괄 선택
                st.markdown("### 일괄 선택 삭제")
                
                # 빠른 선택 옵션
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🔴 유통기한 지난 재료 모두 선택"):
                        today = datetime.now().date()
                        expired_ids = []
                        for _, ingredient in ingredients_df.iterrows():
                            expiry_date = pd.to_datetime(ingredient['expiry_date']).date()
                            if expiry_date < today:
                                expired_ids.append(ingredient['id'])
                        st.session_state['selected_for_deletion'] = expired_ids
                
                with col2:
                    if st.button("🟡 유통기한 임박 재료 모두 선택"):
                        today = datetime.now().date()
                        expiring_ids = []
                        for _, ingredient in ingredients_df.iterrows():
                            expiry_date = pd.to_datetime(ingredient['expiry_date']).date()
                            if today <= expiry_date <= today + timedelta(days=3):
                                expiring_ids.append(ingredient['id'])
                        st.session_state['selected_for_deletion'] = expiring_ids
                
                with col3:
                    if st.button("🗑️ 전체 선택"):
                        st.session_state['selected_for_deletion'] = ingredients_df['id'].tolist()
                
                # 세션 상태 초기화
                if 'selected_for_deletion' not in st.session_state:
                    st.session_state['selected_for_deletion'] = []
                
                st.markdown("---")
                
                # 체크박스로 재료 선택
                selected_ingredients = []
                
                for _, ingredient in ingredients_df.iterrows():
                    # 유통기한 상태 확인
                    today = datetime.now().date()
                    expiry_date = pd.to_datetime(ingredient['expiry_date']).date()
                    
                    if expiry_date < today:
                        status_color = "🔴"
                        status_text = "유통기한 지남"
                    elif expiry_date <= today + timedelta(days=3):
                        status_color = "🟡"
                        status_text = "유통기한 임박"
                    else:
                        status_color = "🟢"
                        status_text = "신선함"
                    
                    # 체크박스 기본값 설정 (세션 상태에 있으면 체크)
                    default_checked = ingredient['id'] in st.session_state['selected_for_deletion']
                    
                    is_selected = st.checkbox(
                        f"{status_color} {ingredient['name']} ({ingredient['category']}) - {ingredient['quantity']}{ingredient['unit']} - {expiry_date} ({status_text})",
                        value=default_checked,
                        key=f"checkbox_{ingredient['id']}"
                    )
                    
                    if is_selected:
                        selected_ingredients.append(ingredient['id'])
                
                # 선택된 재료 삭제
                if selected_ingredients:
                    st.markdown("---")
                    st.warning(f"선택된 재료 {len(selected_ingredients)}개를 삭제하시겠습니까?")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 선택한 재료 삭제", type="primary"):
                            deleted_names = []
                            for ingredient_id in selected_ingredients:
                                ingredient_name = ingredients_df[ingredients_df['id'] == ingredient_id]['name'].iloc[0]
                                deleted_names.append(ingredient_name)
                                db.delete_ingredient(ingredient_id)
                            
                            st.success(f"다음 재료들이 삭제되었습니다: {', '.join(deleted_names)}")
                            # 세션 상태 초기화
                            st.session_state['selected_for_deletion'] = []
                            st.rerun()
                    
                    with col2:
                        if st.button("❌ 선택 취소"):
                            st.session_state['selected_for_deletion'] = []
                            st.rerun()
                else:
                    st.info("삭제할 재료를 선택해주세요.")
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
                
                # 카드 하단에 삭제 버튼 추가
                if st.button(f"🗑️ 삭제", key=f"delete_card_{ingredient['id']}", help=f"{ingredient['name']} 삭제"):
                    # 데이터베이스 매니저 인스턴스 가져오기
                    db = DatabaseManager()
                    db.delete_ingredient(ingredient['id'])
                    st.success(f"'{ingredient['name']}' 재료가 삭제되었습니다.")
                    st.rerun()

def show_recipe_recommendation(db: DatabaseManager):
    """레시피 추천 페이지"""
    st.header("🍳 레시피 추천")
    
    ingredients_df = db.get_ingredients()
    
    if ingredients_df.empty:
        st.warning("냉장고에 재료가 없습니다. '재료 관리' 탭에서 재료를 추가해주세요.")
        return
    
    # AI 추천과 메뉴룰렛을 탭으로 분리
    tab1, tab2 = st.tabs(["🤖 AI 맞춤 추천", "🎯 메뉴룰렛"])
    
    with tab1:
        show_ai_recipe_recommendation(db, ingredients_df)
    
    with tab2:
        show_menu_roulette(db, ingredients_df)

def show_menu_roulette(db: DatabaseManager, ingredients_df):
    """메뉴룰렛 기능"""
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
    
    # 룰렛 결과가 있으면 레시피 추천
    if hasattr(st.session_state, 'roulette_result'):
        st.markdown("---")
        st.subheader(f"🍽️ {st.session_state.roulette_result} 레시피 추천")
        
        # 보유 재료 기반 추천
        available_ingredients = ingredients_df['name'].tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🤖 AI 레시피 생성", use_container_width=True):
                with st.spinner(f"{st.session_state.roulette_result} 레시피를 생성하는 중..."):
                    # 룰렛 결과와 보유 재료를 조합한 프롬프트
                    roulette_prompt = f"{st.session_state.roulette_result} 요리를 만들고 싶습니다. "
                    if difficulty_pref != "상관없음":
                        roulette_prompt += f"난이도는 {difficulty_pref}으로 해주세요. "
                    
                    recipe_gen = RecipeGenerator()
                    recipe = recipe_gen.generate_recipe_from_ingredients(
                        available_ingredients[:10],  # 너무 많은 재료는 제한
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
            display_recipe(recipe, db, "roulette")

def show_ai_recipe_recommendation(db: DatabaseManager, ingredients_df):
    """AI 맞춤 레시피 추천"""
    st.subheader("🤖 AI 맞춤 레시피 추천")
    st.markdown("현재 가지고 있는 재료들을 기반으로 새로운 레시피를 추천받아보세요!")
    
    # 재료를 카테고리별로 분류
    if not ingredients_df.empty:
        categories = ingredients_df['category'].unique()
        selected_ingredients = []
        
        st.markdown("### 📋 카테고리별 재료 선택")
        
        # 카테고리별로 탭 생성
        if len(categories) > 0:
            category_tabs = st.tabs([f"{cat} ({len(ingredients_df[ingredients_df['category'] == cat])}개)" for cat in categories])
            
            for i, category in enumerate(categories):
                with category_tabs[i]:
                    category_ingredients = ingredients_df[ingredients_df['category'] == category]
                    
                    # 카테고리별 전체 선택/해제 버튼
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button(f"전체 선택", key=f"select_all_{category}"):
                            for ingredient in category_ingredients['name']:
                                if f"ingredient_{ingredient}" not in st.session_state:
                                    st.session_state[f"ingredient_{ingredient}"] = True
                            st.rerun()
                    
                    with col2:
                        if st.button(f"전체 해제", key=f"deselect_all_{category}"):
                            for ingredient in category_ingredients['name']:
                                st.session_state[f"ingredient_{ingredient}"] = False
                            st.rerun()
                    
                    # 재료별 체크박스 (3열로 배치)
                    ingredient_list = category_ingredients['name'].tolist()
                    cols = st.columns(3)
                    
                    for idx, ingredient in enumerate(ingredient_list):
                        with cols[idx % 3]:
                            # 유통기한 정보 표시
                            ingredient_info = category_ingredients[category_ingredients['name'] == ingredient].iloc[0]
                            expiry_date = ingredient_info.get('expiry_date')
                            quantity = ingredient_info.get('quantity', 0)
                            unit = ingredient_info.get('unit', '')
                            
                            # 유통기한 상태 확인
                            status_emoji = "🟢"
                            if expiry_date:
                                try:
                                    expiry = pd.to_datetime(expiry_date).date()
                                    today = datetime.now().date()
                                    if expiry < today:
                                        status_emoji = "🔴"
                                    elif expiry <= today + timedelta(days=3):
                                        status_emoji = "🟡"
                                except:
                                    pass
                            
                            # 체크박스 기본값 설정 (처음에는 일부만 선택)
                            default_checked = idx < 3 if f"ingredient_{ingredient}" not in st.session_state else st.session_state.get(f"ingredient_{ingredient}", False)
                            
                            is_selected = st.checkbox(
                                f"{status_emoji} {ingredient} ({quantity}{unit})",
                                value=default_checked,
                                key=f"ingredient_{ingredient}",
                                help=f"유통기한: {expiry_date if expiry_date else '정보 없음'}"
                            )
                            
                            if is_selected:
                                selected_ingredients.append(ingredient)
        
        # 선택된 재료 요약 표시
        if selected_ingredients:
            st.markdown("---")
            st.markdown("### 🥘 선택된 재료")
            
            # 선택된 재료를 카테고리별로 그룹화하여 표시
            selected_by_category = {}
            for ingredient in selected_ingredients:
                ingredient_info = ingredients_df[ingredients_df['name'] == ingredient].iloc[0]
                category = ingredient_info['category']
                if category not in selected_by_category:
                    selected_by_category[category] = []
                selected_by_category[category].append(ingredient)
            
            cols = st.columns(len(selected_by_category))
            for i, (category, ingredients) in enumerate(selected_by_category.items()):
                with cols[i]:
                    st.markdown(f"**{category}**")
                    for ingredient in ingredients:
                        st.write(f"• {ingredient}")
            
            st.info(f"총 {len(selected_ingredients)}개 재료 선택됨")
        else:
            selected_ingredients = []
    else:
        st.warning("등록된 재료가 없습니다.")
        selected_ingredients = []
    
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
                display_recipe(recommended_recipe, db, "ai")
            else:
                st.warning("죄송합니다. 선택하신 재료로 레시피를 생성할 수 없습니다. 다른 재료를 선택하거나 요청사항을 변경해보세요.")

def display_recipe(recipe, db: DatabaseManager, recipe_type: str):
    """레시피 정보를 표시하는 공통 함수"""
    # 레시피 정보 표시
    st.subheader(f"✨ {recipe.get('name', '새로운 레시피')}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("조리 시간", f"{recipe.get('cooking_time', 'N/A')}분")
    with col2:
        st.metric("인분", f"{recipe.get('servings', 'N/A')}인분")
    with col3:
        st.metric("난이도", recipe.get('difficulty', 'N/A'))
    
    # 영양 정보 표시
    if recipe.get('nutrition'):
        st.markdown("---")
        st.subheader("🥗 영양 정보 (1인분 기준)")
        
        col1, col2, col3, col4 = st.columns(4)
        nutrition = recipe['nutrition']
        
        with col1:
            st.metric("칼로리", f"{nutrition.get('calories', 0):.0f} kcal", delta=None)
        with col2:
            st.metric("탄수화물", f"{nutrition.get('carbs', 0):.1f} g", delta=None)
        with col3:
            st.metric("단백질", f"{nutrition.get('protein', 0):.1f} g", delta=None)
        with col4:
            st.metric("지방", f"{nutrition.get('fat', 0):.1f} g", delta=None)
        
        # 영양소 비율 차트
        if nutrition.get('calories', 0) > 0:
            carb_cal = nutrition.get('carbs', 0) * 4
            protein_cal = nutrition.get('protein', 0) * 4
            fat_cal = nutrition.get('fat', 0) * 9
            
            import plotly.express as px
            
            nutrition_data = {
                '영양소': ['탄수화물', '단백질', '지방'],
                '칼로리': [carb_cal, protein_cal, fat_cal],
                '비율(%)': [
                    (carb_cal / nutrition['calories'] * 100) if nutrition['calories'] > 0 else 0,
                    (protein_cal / nutrition['calories'] * 100) if nutrition['calories'] > 0 else 0,
                    (fat_cal / nutrition['calories'] * 100) if nutrition['calories'] > 0 else 0
                ]
            }
            
            fig = px.pie(
                values=nutrition_data['칼로리'],
                names=nutrition_data['영양소'],
                title="영양소 비율",
                color_discrete_sequence=['#D4B8E3', '#B8D4E3', '#F4C2C2']
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("재료")
    for ingredient in recipe.get('ingredients', []):
        st.write(f"- {ingredient.get('name', 'N/A')}: {ingredient.get('quantity', 'N/A')} {ingredient.get('unit', '')}")
        
    st.subheader("조리법")
    instructions = recipe.get('instructions', '조리법이 없습니다.')
    # 줄 바꿈 문자를 기준으로 분리하여 목록으로 표시
    instruction_steps = instructions.split('\n')
    for step in instruction_steps:
        if step.strip(): # 빈 줄 제외
            st.write(f"• {step.strip()}")
    
    if recipe.get('tips'):
        st.subheader("셰프의 팁")
        st.info(recipe['tips'])
    
    # 레시피 저장 버튼
    if st.button(f"이 레시피 저장하기", key=f"save_{recipe_type}"):
        try:
            # 영양 정보 추출
            nutrition = recipe.get('nutrition', {})
            
            db.add_recipe(
                name=recipe.get('name', '이름 없음'),
                ingredients=recipe.get('ingredients', []),
                instructions=recipe.get('instructions', ''),
                cooking_time=recipe.get('cooking_time', 0),
                servings=recipe.get('servings', 0),
                category=recipe.get('category', '기타'),
                difficulty=recipe.get('difficulty', '쉬움'),
                calories=nutrition.get('calories', 0),
                carbs=nutrition.get('carbs', 0),
                protein=nutrition.get('protein', 0),
                fat=nutrition.get('fat', 0)
            )
            st.success("레시피가 성공적으로 저장되었습니다!")
        except Exception as e:
            st.error(f"레시피 저장 중 오류 발생: {str(e)}")

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
                    # 요리 기록 입력 폼 표시
                    with st.form(f"cooking_record_{recipe['id']}"):
                        st.write(f"**{recipe['name']}** 요리 기록을 남겨주세요!")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            rating = st.selectbox("평점", [1, 2, 3, 4, 5], index=4, format_func=lambda x: "⭐" * x, key=f"rating_{recipe['id']}")
                        with col2:
                            cooking_date = st.date_input("요리한 날짜", value=datetime.now().date(), key=f"date_{recipe['id']}")
                        
                        notes = st.text_area("메모 및 후기", placeholder="맛은 어땠나요? 다음에 개선할 점이 있나요?", key=f"notes_{recipe['id']}")
                        
                        if st.form_submit_button("요리 기록 저장"):
                            # 요리 기록 추가
                            if db.add_cooking_history(recipe['id'], rating, notes):
                                st.success(f"'{recipe['name']}' 요리 기록이 저장되었습니다!")
                                st.rerun()
                            else:
                                st.error("요리 기록 저장에 실패했습니다.")
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
                # 직접 입력된 레시피의 경우 ingredients_used에서 레시피명 추출
                if pd.isna(record['recipe_name']):
                    # ingredients_used 형식: "레시피명|재료|조리시간|인분"
                    ingredients_parts = record['ingredients_used'].split('|')
                    if len(ingredients_parts) >= 1:
                        display_recipe_name = ingredients_parts[0]
                    else:
                        display_recipe_name = "직접 입력"
                else:
                    display_recipe_name = record['recipe_name']
                
                with st.expander(f"{display_recipe_name} - {record['cooking_date']} (⭐{record['rating']})"):
                    st.write(f"**요리한 날짜:** {record['cooking_date']}")
                    st.write(f"**평점:** {'⭐' * record['rating']}")
                    
                    # 직접 입력된 레시피의 경우 재료 정보를 더 깔끔하게 표시
                    if pd.isna(record['recipe_name']):
                        ingredients_parts = record['ingredients_used'].split('|')
                        if len(ingredients_parts) >= 2:
                            st.write(f"**사용한 재료:** {ingredients_parts[1]}")
                        if len(ingredients_parts) >= 3:
                            st.write(f"**조리 시간:** {ingredients_parts[2]}")
                        if len(ingredients_parts) >= 4:
                            st.write(f"**인분:** {ingredients_parts[3]}")
                    else:
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
    st.header(" 분석 대시보드")
    
    # 새로고침 버튼
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 새로고침", use_container_width=True):
            st.rerun()
    
    ingredients_df = db.get_ingredients()
    recipes_df = db.get_recipes()
    
    if ingredients_df.empty and recipes_df.empty:
        st.info("아직 데이터가 충분하지 않습니다. 재료를 추가하고 레시피를 저장하여 분석을 시작하세요!")
        return

    # 1. 재료 카테고리 분포 (도넛 차트)
    st.subheader("🥬 재료 카테고리 분포")
    st.markdown("*보유 재료 카테고리별 분포*")
    
    if not ingredients_df.empty:
        category_counts = ingredients_df['category'].value_counts().reset_index()
        category_counts.columns = ['Category', 'Count']
        
        # 도넛 차트 생성 (연한 보라색 중심 파스텔 톤)
        fig = go.Figure(data=[go.Pie(
            labels=category_counts['Category'],
            values=category_counts['Count'],
            hole=0.6,
            marker_colors=['#D4B8E3', '#B8D4E3', '#F4C2C2', '#E6B8E3', '#C2B8E3', '#F0B8E3'],
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig.update_layout(
            title="보유 재료 카테고리별 분포",
            showlegend=True,
            height=400,
            margin=dict(t=50, b=50, l=50, r=50)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("보유 재료 데이터가 없습니다.")

    # 2. 레시피 난이도 분포 (막대 차트)
    st.subheader("🍳 레시피 난이도 분포")
    st.markdown("*레시피 난이도별 분포*")
    
    if not recipes_df.empty:
        difficulty_counts = recipes_df['difficulty'].value_counts().reset_index()
        difficulty_counts.columns = ['Difficulty', 'Count']
        
        fig = px.bar(
            difficulty_counts, 
            x='Difficulty', 
            y='Count',
            title='레시피 난이도별 분포',
            color='Difficulty',
            color_discrete_map={
                '쉬움': '#D4B8E3',
                '보통': '#B8D4E3',
                '어려움': '#F4C2C2'
            }
        )
        
        fig.update_layout(
            xaxis_title="난이도",
            yaxis_title="레시피 수",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("저장된 레시피 데이터가 없습니다.")

    # 3. 인기 레시피 TOP 5 (수평 막대 차트)
    st.subheader("🔥 인기 레시피 TOP 5")
    st.markdown("*가장 많이 사용된 레시피*")
    
    if not recipes_df.empty:
        top_recipes = recipes_df.sort_values(by='used_count', ascending=False).head(5)
        if not top_recipes.empty:
            fig = px.bar(
                top_recipes, 
                y='name', 
                x='used_count',
                orientation='h',
                title='가장 많이 사용된 레시피',
                color='used_count',
                color_continuous_scale='Purples'
            )
            
            fig.update_layout(
                xaxis_title="사용 횟수",
                yaxis_title="레시피 이름",
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("사용된 레시피 데이터가 없습니다.")
    else:
        st.info("저장된 레시피 데이터가 없습니다.")

    # 4. 유통기한 현황 (파이 차트)
    st.subheader("⏰ 유통기한 현황")
    st.markdown("*재료 유통기한 현황*")
    
    if not ingredients_df.empty:
        today = datetime.now().date()
        ingredients_df['expiry_date'] = pd.to_datetime(ingredients_df['expiry_date']).dt.date
        
        # 유통기한 상태 분류
        def classify_expiry(expiry_date):
            if pd.isna(expiry_date):
                return "정보 없음"
            days_left = (expiry_date - today).days
            if days_left < 0:
                return "유통기한 지남"
            elif days_left <= 3:
                return "임박 (3일 이내)"
            else:
                return "신선함"
        
        ingredients_df['expiry_status'] = ingredients_df['expiry_date'].apply(classify_expiry)
        expiry_counts = ingredients_df['expiry_status'].value_counts().reset_index()
        expiry_counts.columns = ['Status', 'Count']
        
        fig = px.pie(
            expiry_counts, 
            values='Count', 
            names='Status',
            title='재료 유통기한 현황',
            color_discrete_map={
                '신선함': '#D4B8E3',
                '임박 (3일 이내)': '#F4C2C2',
                '유통기한 지남': '#E6B8E3',
                '정보 없음': '#B8D4E3'
            }
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("보유 재료 데이터가 없습니다.")

    # 5. 쇼핑 리스트 분석
    st.subheader("🛒 쇼핑 리스트 분석")
    
    conn = db._get_conn()
    
    # 전체 쇼핑 리스트 통계
    total_items = pd.read_sql_query('SELECT COUNT(*) as count FROM shopping_list', conn).iloc[0]['count']
    purchased_items = pd.read_sql_query('SELECT COUNT(*) as count FROM shopping_list WHERE purchased = TRUE', conn).iloc[0]['count']
    pending_items = total_items - purchased_items
    
    if total_items > 0:
        # 키 메트릭 표시
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("전체 품목", total_items)
        with col2:
            completion_rate = (purchased_items / total_items * 100) if total_items > 0 else 0
            st.metric("구매완료", purchased_items, f"{completion_rate:.1f}%")
        with col3:
            st.metric("구매대기", pending_items, f"{(pending_items/total_items*100):.1f}%" if total_items > 0 else "0%")
        with col4:
            st.metric("완료율", f"{completion_rate:.1f}%")
        
        # 구매완료율 도넛 차트
        completion_data = pd.DataFrame({
            '상태': ['구매완료', '구매대기'],
            '개수': [purchased_items, pending_items]
        })
        
        fig = go.Figure(data=[go.Pie(
            labels=completion_data['상태'],
            values=completion_data['개수'],
            hole=0.6,
            marker_colors=['#D4B8E3', '#B8D4E3'],
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig.update_layout(
            title="쇼핑 리스트 구매완료율",
            height=400,
            margin=dict(t=50, b=50, l=50, r=50)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 구매대기 품목 TOP 10
        pending_items_df = pd.read_sql_query('''
            SELECT ingredient_name, quantity, unit, priority
            FROM shopping_list 
            WHERE purchased = FALSE
            ORDER BY priority DESC, created_at ASC
            LIMIT 10
        ''', conn)
        
        if not pending_items_df.empty:
            st.subheader("📋 구매대기 품목 TOP 10")
            
            fig = px.bar(
                pending_items_df,
                x='ingredient_name',
                y='quantity',
                title='구매대기 품목 TOP 10',
                color='priority',
                color_continuous_scale='Purples',
                labels={'ingredient_name': '품목명', 'quantity': '수량', 'priority': '우선순위'}
            )
            
            fig.update_layout(
                xaxis_title="품목명",
                yaxis_title="수량",
                height=400,
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("쇼핑 리스트 데이터가 없습니다.")

    # 6. 인기 식재료 분석 (트리맵)
    st.subheader("🥕 인기 식재료 분석")
    st.markdown("*식재료 사용빈도*")
    
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
            # 상위 15개 재료
            top_ingredients = sorted(ingredient_usage.items(), key=lambda x: x[1], reverse=True)[:15]
            
            if top_ingredients:
                ingredient_df = pd.DataFrame(top_ingredients, columns=['재료명', '사용횟수'])
                
                # 트리맵 차트
                fig = px.treemap(
                    ingredient_df,
                    path=['재료명'],
                    values='사용횟수',
                    title='인기 식재료 분석',
                    color='사용횟수',
                    color_continuous_scale='Purples'
                )
                
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                # 테이블로도 표시
                st.dataframe(ingredient_df, hide_index=True)
            else:
                st.info("사용된 재료 데이터가 없습니다.")
        else:
            st.info("레시피 사용 데이터가 없습니다.")
    else:
        st.info("레시피 데이터가 없습니다.")

    # 7. 월별 요리 활동 분석
    st.subheader("📅 월별 요리 활동 분석")
    
    # 요리 기록 조회
    history_df = pd.read_sql_query('''
        SELECT cooking_date, rating, r.name as recipe_name
        FROM cooking_history ch
        LEFT JOIN recipes r ON ch.recipe_id = r.id
        ORDER BY cooking_date DESC
    ''', conn)
    
    if not history_df.empty:
        history_df['cooking_date'] = pd.to_datetime(history_df['cooking_date'])
        history_df['month'] = history_df['cooking_date'].dt.to_period('M')
        
        monthly_stats = history_df.groupby('month').agg({
            'cooking_date': 'count',
            'rating': 'mean'
        }).reset_index()
        monthly_stats.columns = ['월', '요리 횟수', '평균 평점']
        monthly_stats['월'] = monthly_stats['월'].astype(str)
        
        # 월별 요리 횟수와 평점
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=monthly_stats['월'],
            y=monthly_stats['요리 횟수'],
            mode='lines+markers',
            name='요리 횟수',
            line=dict(color='#D4B8E3', width=3),
            marker=dict(size=8)
        ))
        
        fig.add_trace(go.Scatter(
            x=monthly_stats['월'],
            y=monthly_stats['평균 평점'] * 2,  # 스케일 맞추기
            mode='lines+markers',
            name='평균 평점 (x2)',
            line=dict(color='#B8D4E3', width=3),
            marker=dict(size=8),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='월별 요리 활동 및 평점',
            xaxis_title='월',
            yaxis_title='요리 횟수',
            yaxis2=dict(title='평균 평점', overlaying='y', side='right'),
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("요리 기록 데이터가 없습니다.")

    # 8. 레시피 카테고리별 분포
    st.subheader("🍽️ 레시피 카테고리별 분포")
    
    if not recipes_df.empty:
        category_counts = recipes_df['category'].value_counts().reset_index()
        category_counts.columns = ['Category', 'Count']
        
        # 수평 막대 차트
        fig = px.bar(
            category_counts,
            x='Count',
            y='Category',
            orientation='h',
            title='레시피 카테고리별 분포',
            color='Count',
            color_continuous_scale='Purples'
        )
        
        fig.update_layout(
            xaxis_title="레시피 수",
            yaxis_title="카테고리",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("레시피 데이터가 없습니다.")

    # 9. 조리시간 분포
    st.subheader("⏱️ 조리시간 분포")
    
    if not recipes_df.empty:
        # 조리시간 구간별 분류
        def classify_cooking_time(time):
            if time <= 15:
                return "15분 이내"
            elif time <= 30:
                return "15-30분"
            elif time <= 60:
                return "30분-1시간"
            else:
                return "1시간 이상"
        
        recipes_df['cooking_time_category'] = recipes_df['cooking_time'].apply(classify_cooking_time)
        time_counts = recipes_df['cooking_time_category'].value_counts().reset_index()
        time_counts.columns = ['조리시간', '레시피 수']
        
        fig = px.pie(
            time_counts,
            values='레시피 수',
            names='조리시간',
            title='조리시간별 레시피 분포',
            color_discrete_sequence=['#D4B8E3', '#B8D4E3', '#F4C2C2', '#E6B8E3']
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("레시피 데이터가 없습니다.")

    # 10. 요리 평점 분석
    st.subheader("⭐ 요리 평점 분석")
    
    if not history_df.empty:
        rating_counts = history_df['rating'].value_counts().sort_index().reset_index()
        rating_counts.columns = ['평점', '횟수']
        
        fig = px.bar(
            rating_counts,
            x='평점',
            y='횟수',
            title='요리 평점 분포',
            color='평점',
            color_continuous_scale='Purples',
            text='횟수'
        )
        
        fig.update_layout(
            xaxis_title="평점",
            yaxis_title="요리 횟수",
            height=400,
            showlegend=False
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        # 평균 평점
        avg_rating = history_df['rating'].mean()
        st.metric("전체 평균 평점", f"{avg_rating:.2f}점")

    conn.close()

if __name__ == "__main__":
    main()