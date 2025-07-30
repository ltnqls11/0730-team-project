import openai
import os
from typing import List, Dict, Optional
import json
import base64
from PIL import Image
import io
import streamlit as st

class SmartFridgeAI:
    def __init__(self):
        """OpenAI API 클라이언트 초기화"""
        self.client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
    
    def recommend_recipes(self, ingredients: List[Dict], dietary_preferences: str = "") -> List[Dict]:
        """
        보유 재료를 기반으로 레시피 추천
        """
        try:
            # 재료 목록을 문자열로 변환
            ingredient_list = []
            for ing in ingredients:
                ingredient_list.append(f"{ing['name']} ({ing['quantity']}{ing['unit']})")
            
            ingredients_text = ", ".join(ingredient_list)
            
            prompt = f"""
            다음 재료들을 활용해서 만들 수 있는 한국 요리 레시피 3개를 추천해주세요:
            
            보유 재료: {ingredients_text}
            
            {f"식단 선호도: {dietary_preferences}" if dietary_preferences else ""}
            
            각 레시피는 다음 형식으로 JSON 배열로 응답해주세요:
            [
                {{
                    "name": "요리명",
                    "description": "간단한 설명",
                    "ingredients": "필요한 재료 목록",
                    "instructions": "조리 방법 (단계별로)",
                    "cooking_time": 조리시간(분),
                    "difficulty": "초급/중급/고급",
                    "category": "한식/양식/중식/일식",
                    "nutrition_info": "영양 정보 (칼로리, 주요 영양소)"
                }}
            ]
            
            보유하지 않은 기본 조미료(소금, 후추, 기름 등)는 사용해도 됩니다.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 전문 요리사이자 영양사입니다. 주어진 재료로 맛있고 영양가 있는 한국 요리를 추천해주세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            # JSON 응답 파싱
            content = response.choices[0].message.content
            # JSON 부분만 추출
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            json_content = content[start_idx:end_idx]
            
            recipes = json.loads(json_content)
            return recipes
            
        except Exception as e:
            st.error(f"레시피 추천 중 오류가 발생했습니다: {str(e)}")
            return []
    
    def create_meal_plan(self, days: int, dietary_goals: str, available_ingredients: List[Dict]) -> Dict:
        """
        AI 기반 식단 계획 생성
        """
        try:
            ingredients_text = ", ".join([f"{ing['name']}" for ing in available_ingredients])
            
            prompt = f"""
            {days}일간의 건강한 식단 계획을 세워주세요.
            
            목표: {dietary_goals}
            보유 재료: {ingredients_text}
            
            다음 형식으로 JSON 응답해주세요:
            {{
                "meal_plan": {{
                    "day_1": {{
                        "breakfast": {{"name": "요리명", "calories": 칼로리, "nutrients": "주요 영양소"}},
                        "lunch": {{"name": "요리명", "calories": 칼로리, "nutrients": "주요 영양소"}},
                        "dinner": {{"name": "요리명", "calories": 칼로리, "nutrients": "주요 영양소"}},
                        "snack": {{"name": "간식명", "calories": 칼로리, "nutrients": "주요 영양소"}}
                    }},
                    ...
                }},
                "shopping_list": ["구매가 필요한 재료들"],
                "nutrition_summary": "전체 영양 분석 및 조언"
            }}
            
            균형잡힌 영양소 섭취를 고려하고, 보유 재료를 최대한 활용해주세요.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 전문 영양사입니다. 건강하고 균형잡힌 식단을 계획해주세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            json_content = content[start_idx:end_idx]
            
            meal_plan = json.loads(json_content)
            return meal_plan
            
        except Exception as e:
            st.error(f"식단 계획 생성 중 오류가 발생했습니다: {str(e)}")
            return {}
    
    def analyze_nutrition(self, meal_plan: List[Dict]) -> Dict:
        """
        식단의 영양 분석
        """
        try:
            meals_text = []
            for meal in meal_plan:
                meals_text.append(f"{meal['meal_type']}: {meal['recipe_name']}")
            
            meals_str = "\n".join(meals_text)
            
            prompt = f"""
            다음 식단의 영양을 분석하고 개선 방안을 제시해주세요:
            
            {meals_str}
            
            다음 형식으로 JSON 응답해주세요:
            {{
                "total_calories": 총칼로리,
                "macronutrients": {{
                    "carbs": "탄수화물 비율",
                    "protein": "단백질 비율", 
                    "fat": "지방 비율"
                }},
                "vitamins_minerals": ["부족한 비타민/미네랄"],
                "recommendations": ["개선 방안들"],
                "health_score": 건강점수(1-10),
                "warnings": ["주의사항들"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 전문 영양사입니다. 식단을 분석하고 건강한 조언을 제공해주세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            json_content = content[start_idx:end_idx]
            
            analysis = json.loads(json_content)
            return analysis
            
        except Exception as e:
            st.error(f"영양 분석 중 오류가 발생했습니다: {str(e)}")
            return {}
    
    def recognize_ingredient_from_image(self, image_data: bytes) -> Dict:
        """
        이미지에서 재료 인식
        """
        try:
            # 이미지를 base64로 인코딩
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """이 이미지에 있는 식재료를 분석해서 다음 JSON 형식으로 응답해주세요:
                                {
                                    "ingredients": [
                                        {
                                            "name": "재료명",
                                            "quantity": 예상수량,
                                            "unit": "단위",
                                            "category": "카테고리",
                                            "freshness": "신선도(1-10)",
                                            "estimated_expiry_days": 예상유통기한일수
                                        }
                                    ],
                                    "confidence": 인식신뢰도(1-10)
                                }
                                
                                한국어로 응답하고, 일반적인 식재료만 인식해주세요."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            json_content = content[start_idx:end_idx]
            
            result = json.loads(json_content)
            return result
            
        except Exception as e:
            st.error(f"이미지 인식 중 오류가 발생했습니다: {str(e)}")
            return {"ingredients": [], "confidence": 0}
    
    def get_cooking_assistant(self, recipe_name: str, current_step: int) -> str:
        """
        요리 과정 중 실시간 도움말
        """
        try:
            prompt = f"""
            '{recipe_name}' 요리를 만드는 중입니다. 현재 {current_step}단계에 있습니다.
            
            이 단계에서 주의할 점과 팁을 간단명료하게 알려주세요.
            - 온도, 시간, 기술적 포인트
            - 실패하기 쉬운 부분과 해결책
            - 다음 단계 준비사항
            
            200자 이내로 실용적인 조언을 해주세요.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 친근한 요리 전문가입니다. 실용적이고 간단한 조언을 해주세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"요리 도움말을 가져오는 중 오류가 발생했습니다: {str(e)}"
    
    def suggest_ingredient_substitutes(self, missing_ingredient: str, recipe_context: str) -> List[str]:
        """
        부족한 재료의 대체재 추천
        """
        try:
            prompt = f"""
            '{recipe_context}' 요리에서 '{missing_ingredient}' 재료가 없습니다.
            
            이 재료를 대체할 수 있는 재료들을 추천해주세요.
            - 맛과 식감이 비슷한 것
            - 쉽게 구할 수 있는 것
            - 영양가가 비슷한 것
            
            최대 5개까지 추천하고, 각각 간단한 설명을 붙여주세요.
            JSON 형식으로 응답해주세요:
            [
                {{"substitute": "대체재료", "reason": "추천 이유"}},
                ...
            ]
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 요리 전문가입니다. 실용적인 재료 대체 방안을 제시해주세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            json_content = content[start_idx:end_idx]
            
            substitutes = json.loads(json_content)
            return substitutes
            
        except Exception as e:
            st.error(f"대체재 추천 중 오류가 발생했습니다: {str(e)}")
            return []