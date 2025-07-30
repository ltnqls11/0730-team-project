import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

load_dotenv()

class SupabaseManager:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(url, key)
    
    def create_tables(self):
        """데이터베이스 테이블 생성 (Supabase에서 SQL로 실행)"""
        # 이 함수는 Supabase 대시보드에서 실행할 SQL 쿼리를 제공합니다
        sql_queries = """
        -- 재료 테이블
        CREATE TABLE IF NOT EXISTS ingredients (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            category VARCHAR(50),
            quantity DECIMAL(10,2),
            unit VARCHAR(20),
            expiry_date DATE,
            added_date TIMESTAMP DEFAULT NOW(),
            is_available BOOLEAN DEFAULT TRUE
        );
        
        -- 레시피 테이블
        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            instructions TEXT NOT NULL,
            cooking_time INTEGER,
            servings INTEGER,
            difficulty_level VARCHAR(20),
            created_date TIMESTAMP DEFAULT NOW(),
            usage_count INTEGER DEFAULT 0
        );
        
        -- 레시피-재료 연결 테이블
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_name VARCHAR(100),
            quantity DECIMAL(10,2),
            unit VARCHAR(20),
            is_essential BOOLEAN DEFAULT TRUE
        );
        
        -- 요리 기록 테이블
        CREATE TABLE IF NOT EXISTS cooking_history (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER REFERENCES recipes(id),
            cooked_date TIMESTAMP DEFAULT NOW(),
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            notes TEXT
        );
        
        -- 쇼핑 리스트 테이블
        CREATE TABLE IF NOT EXISTS shopping_list (
            id SERIAL PRIMARY KEY,
            ingredient_name VARCHAR(100),
            quantity DECIMAL(10,2),
            unit VARCHAR(20),
            is_purchased BOOLEAN DEFAULT FALSE,
            added_date TIMESTAMP DEFAULT NOW()
        );
        """
        return sql_queries
    
    def add_ingredient(self, name: str, category: str = None, quantity: float = 0, 
                      unit: str = None, expiry_date: str = None) -> bool:
        """재료 추가"""
        try:
            data = {
                "name": name,
                "category": category,
                "quantity": quantity,
                "unit": unit,
                "expiry_date": expiry_date
            }
            result = self.supabase.table("ingredients").insert(data).execute()
            return True
        except Exception as e:
            print(f"재료 추가 오류: {e}")
            return False
    
    def get_ingredients(self) -> List[Dict]:
        """모든 재료 조회"""
        try:
            result = self.supabase.table("ingredients").select("*").eq("is_available", True).execute()
            return result.data
        except Exception as e:
            print(f"재료 조회 오류: {e}")
            return []
    
    def add_recipe(self, title: str, description: str, instructions: str, 
                   ingredients: List[Dict], cooking_time: int = None, 
                   servings: int = None, difficulty: str = "보통") -> bool:
        """레시피 추가"""
        try:
            print(f"레시피 저장 시도: {title}")
            print(f"재료 개수: {len(ingredients)}")
            
            # 레시피 기본 정보 추가
            recipe_data = {
                "title": title,
                "description": description,
                "instructions": instructions,
                "cooking_time": cooking_time,
                "servings": servings,
                "difficulty_level": difficulty
            }
            
            print(f"레시피 데이터: {recipe_data}")
            recipe_result = self.supabase.table("recipes").insert(recipe_data).execute()
            
            if not recipe_result.data:
                print("레시피 저장 실패: 데이터가 반환되지 않음")
                return False
                
            recipe_id = recipe_result.data[0]["id"]
            print(f"레시피 ID: {recipe_id}")
            
            # 레시피 재료 추가
            for i, ingredient in enumerate(ingredients):
                ingredient_data = {
                    "recipe_id": recipe_id,
                    "ingredient_name": ingredient.get("name"),
                    "quantity": ingredient.get("quantity"),
                    "unit": ingredient.get("unit"),
                    "is_essential": ingredient.get("is_essential", True)
                }
                print(f"재료 {i+1}: {ingredient_data}")
                ingredient_result = self.supabase.table("recipe_ingredients").insert(ingredient_data).execute()
                if not ingredient_result.data:
                    print(f"재료 {i+1} 저장 실패")
            
            print("레시피 저장 완료")
            return True
        except Exception as e:
            print(f"레시피 추가 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_recipes(self) -> List[Dict]:
        """모든 레시피 조회"""
        try:
            result = self.supabase.table("recipes").select("*").execute()
            return result.data
        except Exception as e:
            print(f"레시피 조회 오류: {e}")
            return []
    
    def get_recipe_with_ingredients(self, recipe_id: int) -> Dict:
        """특정 레시피와 재료 정보 조회"""
        try:
            # 레시피 기본 정보
            recipe_result = self.supabase.table("recipes").select("*").eq("id", recipe_id).execute()
            recipe = recipe_result.data[0] if recipe_result.data else None
            
            # 레시피 재료 정보
            ingredients_result = self.supabase.table("recipe_ingredients").select("*").eq("recipe_id", recipe_id).execute()
            ingredients = ingredients_result.data
            
            if recipe:
                recipe["ingredients"] = ingredients
            
            return recipe
        except Exception as e:
            print(f"레시피 상세 조회 오류: {e}")
            return {}
    
    def add_cooking_history(self, recipe_id: int, rating: int = None, notes: str = None) -> bool:
        """요리 기록 추가"""
        try:
            data = {
                "recipe_id": recipe_id,
                "rating": rating,
                "notes": notes
            }
            self.supabase.table("cooking_history").insert(data).execute()
            
            # 레시피 사용 횟수 증가
            self.supabase.table("recipes").update({"usage_count": "usage_count + 1"}).eq("id", recipe_id).execute()
            
            return True
        except Exception as e:
            print(f"요리 기록 추가 오류: {e}")
            return False
    
    def get_cooking_statistics(self) -> Dict:
        """요리 통계 조회"""
        try:
            # 총 요리 횟수
            total_cooking = self.supabase.table("cooking_history").select("id", count="exact").execute()
            
            # 인기 레시피 (사용 횟수 기준)
            popular_recipes = self.supabase.table("recipes").select("title, usage_count").order("usage_count", desc=True).limit(5).execute()
            
            # 월별 요리 횟수
            monthly_cooking = self.supabase.table("cooking_history").select("cooked_date").execute()
            
            return {
                "total_cooking": total_cooking.count if hasattr(total_cooking, 'count') else 0,
                "popular_recipes": popular_recipes.data,
                "monthly_data": monthly_cooking.data
            }
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {}
    
    def add_to_shopping_list(self, ingredient_name: str, quantity: float, unit: str) -> bool:
        """쇼핑 리스트에 재료 추가"""
        try:
            print(f"쇼핑 리스트 추가 시도: {ingredient_name} {quantity} {unit}")
            
            data = {
                "ingredient_name": ingredient_name,
                "quantity": quantity,
                "unit": unit
            }
            
            result = self.supabase.table("shopping_list").insert(data).execute()
            
            if result.data:
                print(f"쇼핑 리스트 추가 성공: {result.data}")
                return True
            else:
                print("쇼핑 리스트 추가 실패: 데이터가 반환되지 않음")
                return False
                
        except Exception as e:
            print(f"쇼핑 리스트 추가 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_shopping_list(self) -> List[Dict]:
        """쇼핑 리스트 조회"""
        try:
            result = self.supabase.table("shopping_list").select("*").eq("is_purchased", False).execute()
            return result.data
        except Exception as e:
            print(f"쇼핑 리스트 조회 오류: {e}")
            return []