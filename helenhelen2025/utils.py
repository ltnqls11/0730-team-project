import os
import openai
from PIL import Image
import base64
import io
import numpy as np
from typing import List, Dict
import json
import re
from dotenv import load_dotenv

load_dotenv()

class ImageProcessor:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
    
    def encode_image_to_base64(self, image):
        """PIL Image를 base64로 인코딩"""
        try:
            # PIL Image를 bytes로 변환
            if isinstance(image, Image.Image):
                buffer = io.BytesIO()
                image.save(buffer, format='JPEG')
                image_bytes = buffer.getvalue()
                return base64.b64encode(image_bytes).decode('utf-8')
            else:
                raise ValueError("지원하지 않는 이미지 형식입니다.")
        except Exception as e:
            print(f"이미지 인코딩 오류: {e}")
            return None
    
    def extract_text_from_image(self, image) -> str:
        """이미지에서 텍스트 추출 (OpenAI Vision API 사용)"""
        try:
            base64_image = self.encode_image_to_base64(image)
            if not base64_image:
                return ""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "이 이미지에서 보이는 모든 텍스트를 추출해주세요. 한국어와 영어 모두 인식해주세요."
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
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"텍스트 추출 오류: {e}")
            return ""
    
    def identify_ingredients_from_image(self, image) -> List[Dict]:
        """이미지에서 직접 재료 식별 (더 정확한 방법)"""
        try:
            base64_image = self.encode_image_to_base64(image)
            if not base64_image:
                return []
            
            prompt = """
            이 이미지에서 보이는 음식 재료들을 식별해주세요. 
            냉장고, 식료품, 요리 재료 등을 찾아서 다음 JSON 형식으로 반환해주세요:
            
            {
                "ingredients": [
                    {
                        "name": "재료명 (한국어)",
                        "category": "카테고리 (채소, 육류, 유제품, 조미료, 곡물, 기타 중 하나)",
                        "quantity": 1,
                        "unit": "단위 (개, kg, g, L, ml, 팩, 봉 중 하나)",
                        "freshness": "신선도 (신선, 보통, 주의 중 하나)",
                        "confidence": 0.9
                    }
                ]
            }
            
            실제로 보이는 재료만 포함하고, 확실하지 않은 것은 제외해주세요.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
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
                max_tokens=1000
            )
            
            result = response.choices[0].message.content
            
            try:
                # JSON 파싱
                ingredients_data = json.loads(result)
                return ingredients_data.get("ingredients", [])
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트에서 재료 추출
                return self._extract_ingredients_from_text_fallback(result)
                
        except Exception as e:
            print(f"재료 식별 오류: {e}")
            return []
    
    def _extract_ingredients_from_text_fallback(self, text: str) -> List[Dict]:
        """텍스트에서 재료 추출 (fallback 방법)"""
        common_ingredients = [
            "양파", "마늘", "생강", "대파", "당근", "감자", "토마토", "오이", "배추",
            "쌀", "밀가루", "계란", "우유", "치즈", "버터", "소금", "설탕", "간장",
            "고추장", "된장", "참기름", "식용유", "돼지고기", "소고기", "닭고기",
            "생선", "새우", "두부", "콩나물", "시금치", "상추", "김치", "라면"
        ]
        
        found_ingredients = []
        for ingredient in common_ingredients:
            if ingredient in text:
                found_ingredients.append({
                    "name": ingredient,
                    "category": "기타",
                    "quantity": 1,
                    "unit": "개",
                    "freshness": "보통",
                    "confidence": 0.7
                })
        
        return found_ingredients
    
    def preprocess_image(self, image) -> Image.Image:
        """이미지 전처리 (PIL Image 반환)"""
        try:
            if isinstance(image, Image.Image):
                # 이미지 크기 조정 (너무 큰 이미지는 API 호출 시 문제가 될 수 있음)
                max_size = (1024, 1024)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # RGB 모드로 변환
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                return image
            else:
                raise ValueError("PIL Image 형식이 아닙니다.")
        except Exception as e:
            print(f"이미지 전처리 오류: {e}")
            return image

class OpenAIManager:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.client = openai.OpenAI()
    
    def extract_ingredients_from_text(self, text: str) -> List[Dict]:
        """텍스트에서 재료 정보 추출"""
        try:
            prompt = f"""
            다음 텍스트에서 음식 재료를 추출하고 JSON 형태로 반환해주세요.
            각 재료는 name, category, quantity, unit 정보를 포함해야 합니다.
            
            텍스트: {text}
            
            응답 형식:
            {{
                "ingredients": [
                    {{
                        "name": "재료명",
                        "category": "카테고리 (채소, 육류, 유제품, 조미료 등)",
                        "quantity": 수량 (숫자만, 없으면 1),
                        "unit": "단위 (개, kg, g, ml, L 등, 없으면 '개')"
                    }}
                ]
            }}
            
            한국어로 응답하고, 음식 재료가 아닌 것은 제외해주세요.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            
            # JSON 파싱
            try:
                ingredients_data = json.loads(result)
                return ingredients_data.get("ingredients", [])
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 정규식으로 재료 추출
                return self._extract_ingredients_fallback(text)
                
        except Exception as e:
            print(f"재료 추출 오류: {e}")
            return []
    
    def _extract_ingredients_fallback(self, text: str) -> List[Dict]:
        """재료 추출 대체 방법"""
        common_ingredients = [
            "양파", "마늘", "생강", "대파", "당근", "감자", "토마토", "오이", "배추",
            "쌀", "밀가루", "계란", "우유", "치즈", "버터", "소금", "설탕", "간장",
            "고추장", "된장", "참기름", "식용유", "돼지고기", "소고기", "닭고기",
            "생선", "새우", "두부", "콩나물", "시금치", "상추"
        ]
        
        found_ingredients = []
        for ingredient in common_ingredients:
            if ingredient in text:
                found_ingredients.append({
                    "name": ingredient,
                    "category": "기타",
                    "quantity": 1,
                    "unit": "개"
                })
        
        return found_ingredients
    
    def generate_recipe(self, available_ingredients: List[str], preferences: str = "") -> Dict:
        """사용 가능한 재료로 레시피 생성"""
        try:
            ingredients_text = ", ".join(available_ingredients)
            
            prompt = f"""
            다음 재료들을 사용해서 맛있는 한국 가정식 레시피를 만들어주세요:
            재료: {ingredients_text}
            
            선호사항: {preferences}
            
            다음 JSON 형식으로 응답해주세요:
            {{
                "title": "요리 제목",
                "description": "요리 설명 (2-3줄)",
                "cooking_time": 조리시간(분),
                "servings": 인분수,
                "difficulty": "쉬움/보통/어려움",
                "ingredients": [
                    {{
                        "name": "재료명",
                        "quantity": 수량,
                        "unit": "단위",
                        "is_essential": true/false
                    }}
                ],
                "instructions": [
                    "조리 단계 1",
                    "조리 단계 2",
                    "조리 단계 3"
                ],
                "tips": [
                    "요리 팁 1",
                    "요리 팁 2"
                ]
            }}
            
            실제로 만들 수 있는 현실적인 레시피를 제안해주세요.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            
            try:
                recipe_data = json.loads(result)
                return recipe_data
            except json.JSONDecodeError:
                return {
                    "title": "추천 레시피",
                    "description": "사용 가능한 재료로 만들 수 있는 요리입니다.",
                    "cooking_time": 30,
                    "servings": 2,
                    "difficulty": "보통",
                    "ingredients": [{"name": ing, "quantity": 1, "unit": "개", "is_essential": True} for ing in available_ingredients],
                    "instructions": ["재료를 준비합니다.", "조리합니다.", "완성합니다."],
                    "tips": ["맛있게 드세요!"]
                }
                
        except Exception as e:
            print(f"레시피 생성 오류: {e}")
            return {}
    
    def suggest_missing_ingredients(self, recipe_ingredients: List[str], 
                                  available_ingredients: List[str]) -> List[str]:
        """부족한 재료 추천"""
        try:
            available_set = set(available_ingredients)
            recipe_set = set(recipe_ingredients)
            missing = list(recipe_set - available_set)
            
            if not missing:
                return []
            
            prompt = f"""
            다음 레시피에 필요한 재료 중 부족한 재료들입니다:
            부족한 재료: {', '.join(missing)}
            보유 재료: {', '.join(available_ingredients)}
            
            부족한 재료 중에서 꼭 필요한 것과 대체 가능한 것을 구분해서 
            JSON 형식으로 알려주세요:
            
            {{
                "essential": ["꼭 필요한 재료들"],
                "optional": ["선택적 재료들"],
                "substitutes": [
                    {{
                        "original": "원래 재료",
                        "substitute": "대체 재료",
                        "note": "대체 시 주의사항"
                    }}
                ]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {
                    "essential": missing,
                    "optional": [],
                    "substitutes": []
                }
                
        except Exception as e:
            print(f"부족한 재료 분석 오류: {e}")
            return {"essential": missing if 'missing' in locals() else [], "optional": [], "substitutes": []}

def format_recipe_for_display(recipe: Dict) -> str:
    """레시피를 표시용 텍스트로 포맷팅"""
    if not recipe:
        return "레시피를 생성할 수 없습니다."
    
    formatted = f"""
    ## {recipe.get('title', '제목 없음')}
    
    **설명:** {recipe.get('description', '설명 없음')}
    
    **조리시간:** {recipe.get('cooking_time', '미정')}분  
    **인분:** {recipe.get('servings', '미정')}인분  
    **난이도:** {recipe.get('difficulty', '보통')}
    
    ### 재료
    """
    
    ingredients = recipe.get('ingredients', [])
    for ing in ingredients:
        essential = "✅" if ing.get('is_essential', True) else "⭕"
        formatted += f"- {essential} {ing.get('name', '')} {ing.get('quantity', '')} {ing.get('unit', '')}\n"
    
    formatted += "\n### 조리법\n"
    instructions = recipe.get('instructions', [])
    for i, step in enumerate(instructions, 1):
        formatted += f"{i}. {step}\n"
    
    tips = recipe.get('tips', [])
    if tips:
        formatted += "\n### 요리 팁\n"
        for tip in tips:
            formatted += f"💡 {tip}\n"
    
    return formatted