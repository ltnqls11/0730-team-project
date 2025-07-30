from config import SUPABASE_URL, SUPABASE_KEY, INGREDIENTS_TABLE, RECIPES_TABLE, MEAL_PLANS_TABLE, USERS_TABLE, TEST_MODE
from datetime import datetime, date, timedelta
import pandas as pd
from typing import List, Dict, Optional
import uuid

class SmartFridgeDB:
    def __init__(self):
        """Supabase 클라이언트 초기화"""
        if TEST_MODE:
            self.test_mode = True
            self.test_data = {
                'users': {},
                'ingredients': {},
                'recipes': {},
                'meal_plans': {}
            }
        else:
            self.test_mode = False
            try:
                from supabase import create_client, Client
                self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            except ImportError:
                print("Supabase 모듈을 찾을 수 없습니다. 테스트 모드로 전환합니다.")
                self.test_mode = True
                self.test_data = {
                    'users': {},
                    'ingredients': {},
                    'recipes': {},
                    'meal_plans': {}
                }
            except Exception as e:
                print(f"Supabase 연결 오류: {e}. 테스트 모드로 전환합니다.")
                self.test_mode = True
                self.test_data = {
                    'users': {},
                    'ingredients': {},
                    'recipes': {},
                    'meal_plans': {}
                }
    
    def get_user_id(self, email: str) -> Optional[str]:
        """이메일로 사용자 ID 조회"""
        if self.test_mode:
            for user_id, user_data in self.test_data['users'].items():
                if user_data['email'] == email:
                    return user_id
            return None
        
        try:
            response = self.supabase.table(USERS_TABLE).select("id").eq("email", email).execute()
            if response.data:
                return response.data[0]["id"]
            return None
        except Exception as e:
            print(f"사용자 조회 오류: {e}")
            return None
    
    def create_user(self, email: str, name: str) -> Optional[str]:
        """새 사용자 생성"""
        if self.test_mode:
            user_id = str(uuid.uuid4())
            self.test_data['users'][user_id] = {
                'email': email,
                'name': name,
                'created_at': datetime.now().isoformat()
            }
            return user_id
        
        try:
            response = self.supabase.table(USERS_TABLE).insert({
                "email": email,
                "name": name
            }).execute()
            return response.data[0]["id"] if response.data else None
        except Exception as e:
            print(f"사용자 생성 오류: {e}")
            return None
    
    # 식재료 관련 메서드
    def add_ingredient(self, user_id: str, name: str, quantity: float, unit: str, 
                       purchase_date: date, expiry_date: date, category: str = None, 
                       location: str = "냉장고") -> bool:
        """새 식재료 추가"""
        if self.test_mode:
            ingredient_id = str(uuid.uuid4())
            self.test_data['ingredients'][ingredient_id] = {
                'user_id': user_id,
                'name': name,
                'quantity': quantity,
                'unit': unit,
                'purchase_date': purchase_date.isoformat(),
                'expiry_date': expiry_date.isoformat(),
                'category': category,
                'location': location,
                'is_expired': expiry_date < date.today(),
                'created_at': datetime.now().isoformat()
            }
            return True
        
        try:
            response = self.supabase.table(INGREDIENTS_TABLE).insert({
                "user_id": user_id,
                "name": name,
                "quantity": quantity,
                "unit": unit,
                "purchase_date": purchase_date.isoformat(),
                "expiry_date": expiry_date.isoformat(),
                "category": category,
                "location": location
            }).execute()
            return bool(response.data)
        except Exception as e:
            print(f"식재료 추가 오류: {e}")
            return False
    
    def get_ingredients(self, user_id: str) -> List[Dict]:
        """사용자의 모든 식재료 조회"""
        if self.test_mode:
            ingredients = []
            for ingredient_id, ingredient in self.test_data['ingredients'].items():
                if ingredient['user_id'] == user_id:
                    ingredient_copy = ingredient.copy()
                    ingredient_copy['id'] = ingredient_id
                    ingredients.append(ingredient_copy)
            return ingredients
        
        try:
            response = self.supabase.table(INGREDIENTS_TABLE).select("*").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            print(f"식재료 조회 오류: {e}")
            return []
    
    def get_expiring_ingredients(self, user_id: str, days: int = 7) -> List[Dict]:
        """유통기한이 임박한 식재료 조회"""
        if self.test_mode:
            future_date = date.today() + timedelta(days=days)
            return [ingredient for ingredient in self.test_data['ingredients'].values()
                   if ingredient['user_id'] == user_id and 
                   datetime.strptime(ingredient['expiry_date'], "%Y-%m-%d").date() <= future_date]
        
        try:
            future_date = date.today() + timedelta(days=days)
            response = self.supabase.table(INGREDIENTS_TABLE).select("*").eq("user_id", user_id).lte("expiry_date", future_date.isoformat()).execute()
            return response.data
        except Exception as e:
            print(f"임박 식재료 조회 오류: {e}")
            return []
    
    def update_ingredient(self, ingredient_id: str, **kwargs) -> bool:
        """식재료 정보 업데이트"""
        if self.test_mode:
            if ingredient_id in self.test_data['ingredients']:
                self.test_data['ingredients'][ingredient_id].update(kwargs)
                return True
            return False
        
        try:
            response = self.supabase.table(INGREDIENTS_TABLE).update(kwargs).eq("id", ingredient_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"식재료 업데이트 오류: {e}")
            return False
    
    def delete_ingredient(self, ingredient_id: str) -> bool:
        """식재료 삭제"""
        if self.test_mode:
            if ingredient_id in self.test_data['ingredients']:
                del self.test_data['ingredients'][ingredient_id]
                return True
            return False
        
        try:
            response = self.supabase.table(INGREDIENTS_TABLE).delete().eq("id", ingredient_id).execute()
            return True
        except Exception as e:
            print(f"식재료 삭제 오류: {e}")
            return False
    
    # 레시피 관련 메서드
    def add_recipe(self, user_id: str, name: str, description: str = None, 
                   ingredients_list: str = None, cooking_time: int = None, 
                   difficulty: str = None, category: str = None, 
                   image_url: str = None) -> bool:
        """새 레시피 추가"""
        if self.test_mode:
            recipe_id = str(uuid.uuid4())
            self.test_data['recipes'][recipe_id] = {
                'user_id': user_id,
                'name': name,
                'description': description,
                'ingredients_list': ingredients_list,
                'cooking_time': cooking_time,
                'difficulty': difficulty,
                'category': category,
                'image_url': image_url,
                'created_at': datetime.now().isoformat()
            }
            return True
        
        try:
            response = self.supabase.table(RECIPES_TABLE).insert({
                "user_id": user_id,
                "name": name,
                "description": description,
                "ingredients_list": ingredients_list,
                "cooking_time": cooking_time,
                "difficulty": difficulty,
                "category": category,
                "image_url": image_url
            }).execute()
            return bool(response.data)
        except Exception as e:
            print(f"레시피 추가 오류: {e}")
            return False
    
    def get_recipes(self, user_id: str) -> List[Dict]:
        """사용자의 모든 레시피 조회"""
        if self.test_mode:
            return [recipe for recipe in self.test_data['recipes'].values() 
                   if recipe['user_id'] == user_id]
        
        try:
            response = self.supabase.table(RECIPES_TABLE).select("*").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            print(f"레시피 조회 오류: {e}")
            return []
    
    def get_recipes_by_category(self, user_id: str, category: str) -> List[Dict]:
        """카테고리별 레시피 조회"""
        if self.test_mode:
            return [recipe for recipe in self.test_data['recipes'].values()
                   if recipe['user_id'] == user_id and recipe['category'] == category]
        
        try:
            response = self.supabase.table(RECIPES_TABLE).select("*").eq("user_id", user_id).eq("category", category).execute()
            return response.data
        except Exception as e:
            print(f"카테고리별 레시피 조회 오류: {e}")
            return []
    
    # 식단 계획 관련 메서드
    def add_meal_plan(self, user_id: str, recipe_id: str, plan_date: date, 
                      meal_type: str, notes: str = None) -> bool:
        """새 식단 계획 추가"""
        if self.test_mode:
            meal_plan_id = str(uuid.uuid4())
            self.test_data['meal_plans'][meal_plan_id] = {
                'user_id': user_id,
                'recipe_id': recipe_id,
                'plan_date': plan_date.isoformat(),
                'meal_type': meal_type,
                'notes': notes,
                'created_at': datetime.now().isoformat()
            }
            return True
        
        try:
            response = self.supabase.table(MEAL_PLANS_TABLE).insert({
                "user_id": user_id,
                "recipe_id": recipe_id,
                "plan_date": plan_date.isoformat(),
                "meal_type": meal_type,
                "notes": notes
            }).execute()
            return bool(response.data)
        except Exception as e:
            print(f"식단 계획 추가 오류: {e}")
            return False
    
    def get_meal_plans(self, user_id: str, start_date: date = None, end_date: date = None) -> List[Dict]:
        """식단 계획 조회"""
        if self.test_mode:
            plans = [plan for plan in self.test_data['meal_plans'].values() 
                    if plan['user_id'] == user_id]
            
            if start_date:
                plans = [plan for plan in plans 
                        if datetime.strptime(plan['plan_date'], "%Y-%m-%d").date() >= start_date]
            if end_date:
                plans = [plan for plan in plans 
                        if datetime.strptime(plan['plan_date'], "%Y-%m-%d").date() <= end_date]
            
            # 레시피 정보 추가
            for plan in plans:
                recipe_id = plan['recipe_id']
                plan['recipes'] = self.test_data['recipes'].get(recipe_id, {})
            
            return plans
        
        try:
            query = self.supabase.table(MEAL_PLANS_TABLE).select("*, recipes(*)").eq("user_id", user_id)
            
            if start_date:
                query = query.gte("plan_date", start_date.isoformat())
            if end_date:
                query = query.lte("plan_date", end_date.isoformat())
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"식단 계획 조회 오류: {e}")
            return []
    
    def delete_meal_plan(self, meal_plan_id: str) -> bool:
        """식단 계획 삭제"""
        if self.test_mode:
            if meal_plan_id in self.test_data['meal_plans']:
                del self.test_data['meal_plans'][meal_plan_id]
                return True
            return False
        
        try:
            response = self.supabase.table(MEAL_PLANS_TABLE).delete().eq("id", meal_plan_id).execute()
            return True
        except Exception as e:
            print(f"식단 계획 삭제 오류: {e}")
            return False
    
    # 통계 및 분석 메서드
    def get_ingredient_statistics(self, user_id: str) -> Dict:
        """식재료 통계 정보"""
        try:
            ingredients = self.get_ingredients(user_id)
            if not ingredients:
                return {"total": 0, "expired": 0, "expiring_soon": 0, "categories": {}}
            
            total = len(ingredients)
            
            # 만료된 재료 수 계산
            expired = 0
            for ingredient in ingredients:
                if 'expiry_date' in ingredient:
                    expiry_date = datetime.strptime(ingredient['expiry_date'], "%Y-%m-%d").date()
                    if expiry_date < date.today():
                        expired += 1
            
            expiring_soon = len(self.get_expiring_ingredients(user_id, 3))
            
            categories = {}
            for ingredient in ingredients:
                category = ingredient.get("category", "기타")
                categories[category] = categories.get(category, 0) + 1
            
            return {
                "total": total,
                "expired": expired,
                "expiring_soon": expiring_soon,
                "categories": categories
            }
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {"total": 0, "expired": 0, "expiring_soon": 0, "categories": {}} 