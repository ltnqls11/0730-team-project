import os
from flask import Flask, request, jsonify
import openai
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash # Flask 표준 비밀번호 해싱
import jwt # JWT (JSON Web Token) 라이브러리
from datetime import datetime, timedelta
import sqlite3

# .env 파일에서 환경 변수 로드
load_dotenv()

app = Flask(__name__)

# CORS 헤더를 수동으로 추가하는 함수
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# OPTIONS 요청 처리 (preflight 요청)
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return '', 200

# --- 환경 변수 설정 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY 환경 변수가 설정되지 않았습니다.")

# OpenAI 클라이언트 초기화 (새로운 방식)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ===== OpenAI 모델 설정 =====
# GPT-4o-mini 모델만 사용 (가성비 최고! 빠르고 저렴함)
# 다른 모델 사용을 원할 경우 아래 상수만 변경하면 됩니다.
OPENAI_MODEL = "gpt-4o-mini"

# --- 데이터베이스 연결 유틸리티 함수 ---
def get_db_connection():
    """데이터베이스 연결 객체를 반환합니다."""
    try:
        conn = sqlite3.connect('recipe_management.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"데이터베이스 연결 오류: {e}")
        return None

# --- JWT 토큰 생성 및 검증 헬퍼 함수 ---
def generate_token(user_id):
    """주어진 user_id로 JWT 토큰을 생성합니다."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=1) # 토큰 만료 시간 (1일)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """JWT 토큰을 검증하고 유효하면 user_id를 반환합니다."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None # 토큰 만료
    except jwt.InvalidTokenError:
        return None # 유효하지 않은 토큰

# --- 미들웨어: 토큰 검증 데코레이터 ---
def token_required(f):
    """API 요청 시 JWT 토큰을 검증하는 데코레이터."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # 요청 헤더에서 Authorization: Bearer <token> 형식으로 토큰 가져오기
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({"message": "인증 토큰이 누락되었습니다."}), 401

        current_user_id = verify_token(token)
        if current_user_id is None:
            return jsonify({"message": "유효하지 않거나 만료된 토큰입니다."}), 401

        return f(current_user_id, *args, **kwargs)
    return decorated

# --- API 엔드포인트 ---

@app.route('/')
def home():
    """기본 홈 경로."""
    return '''
    <html>
    <head><title>레시피 관리 시스템</title></head>
    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
        <h1>🍳 레시피 관리 시스템 백엔드 API</h1>
        <p style="color: green; font-size: 18px;">✅ 서버가 정상적으로 실행 중입니다!</p>
        <p style="color: blue; font-size: 14px;">🤖 AI 모델: GPT-4o-mini (가성비 최고!)</p>
        <div style="margin: 30px;">
            <h3>API 엔드포인트:</h3>
            <ul style="list-style: none; padding: 0;">
                <li>🔗 <a href="/api/test">GET /api/test</a> - 연결 테스트</li>
                <li>📝 POST /api/register - 회원가입</li>
                <li>🔐 POST /api/login - 로그인</li>
                <li>🥕 GET /api/user_ingredients - 재료 목록</li>
                <li>✨ POST /api/recommend_recipes - GPT 레시피 추천</li>
                <li>🛒 POST /api/smart-ingredient-suggestions - GPT 재료 추천</li>
            </ul>
        </div>
        <div style="margin: 30px;">
            <button onclick="createSampleData()" style="background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
                🎯 샘플 데이터 생성하기
            </button>
            <div style="font-size: 12px; color: #666; margin-top: 10px;">
                <p><strong>📱 데모 계정들:</strong></p>
                <p>• demo_user / demo123 (기본 10가지 재료)</p>
                <p>• 1 / 1103 (맞춤 15가지 재료)</p>
            </div>
        </div>
        <script>
        async function createSampleData() {
            try {
                const response = await fetch('/api/create-sample-data', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                const data = await response.json();
                alert(data.message || '샘플 데이터가 생성되었습니다!');
            } catch (error) {
                alert('오류가 발생했습니다: ' + error.message);
            }
        }
        </script>
        <p style="color: #666;">포트: 5000 | 시간: ''' + str(datetime.now()) + '''</p>
    </body>
    </html>
    '''

@app.route('/api/test', methods=['GET'])
def test_api():
    """API 연결 테스트용 엔드포인트."""
    return jsonify({
        "message": "API 연결 성공!", 
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "server": "Flask Recipe Management API"
    })

# --- 1. 사용자 인증 API ---
@app.route('/api/register', methods=['POST'])
def register_user():
    """새로운 사용자를 등록합니다."""
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({"error": "사용자 이름, 이메일, 비밀번호는 필수입니다."}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # 사용자 이름 또는 이메일 중복 확인
        cursor.execute("SELECT user_id FROM Users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            return jsonify({"error": "이미 존재하는 사용자 이름 또는 이메일입니다."}), 409

        # 새 사용자 데이터 구조 (요청한 형식대로)
        new_user = {
            'username': data['username'],
            'email': data['email'],
            'password_hash': generate_password_hash(data['password'])
        }

        sql = "INSERT INTO Users (username, email, password_hash) VALUES (?, ?, ?)"
        cursor.execute(sql, (new_user['username'], new_user['email'], new_user['password_hash']))
        conn.commit()
        return jsonify({"message": "사용자 등록 성공!", "user_id": cursor.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        print(f"사용자 등록 오류: {e}")
        return jsonify({"error": f"사용자 등록 오류: {e}"}), 500
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login_user():
    """사용자 로그인을 처리하고 JWT 토큰을 발급합니다."""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({"error": "사용자 이름과 비밀번호는 필수입니다."}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, password_hash FROM Users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            token = generate_token(user['user_id'])
            return jsonify({"message": "로그인 성공!", "token": token, "user_id": user['user_id']}), 200
        else:
            return jsonify({"error": "잘못된 사용자 이름 또는 비밀번호입니다."}), 401
    except Exception as e:
        print(f"로그인 오류: {e}")
        return jsonify({"error": f"로그인 오류: {e}"}), 500
    finally:
        conn.close()

# --- 2. 재료 관리 API ---
@app.route('/api/user_ingredients', methods=['GET'])
@token_required
def get_user_ingredients(current_user_id):
    """현재 로그인한 사용자의 보유 재료 목록을 조회합니다."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        sql = """
            SELECT ui.user_ingredient_id, ui.quantity, ui.purchase_date, ui.expiration_date, ui.location,
                   i.ingredient_name, i.category, i.unit, i.image_url
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            WHERE ui.user_id = ?
            ORDER BY ui.expiration_date ASC
        """
        cursor.execute(sql, (current_user_id,))
        ingredients = cursor.fetchall()
        return jsonify({"status": "success", "ingredients": [dict(row) for row in ingredients]})
    except Exception as e:
        print(f"보유 재료 조회 오류: {e}")
        return jsonify({"error": f"보유 재료 조회 오류: {e}"}), 500
    finally:
        conn.close()

@app.route('/api/user_ingredients', methods=['POST'])
@token_required
def add_user_ingredient(current_user_id):
    """현재 로그인한 사용자의 보유 재료를 추가합니다."""
    data = request.json
    ingredient_name = data.get('ingredient_name')
    quantity = data.get('quantity')
    purchase_date = data.get('purchase_date') # YYYY-MM-DD 형식
    expiration_date = data.get('expiration_date') # YYYY-MM-DD 형식
    location = data.get('location') # 예: 냉장실, 냉동실, 상온

    if not all([ingredient_name, quantity, expiration_date]):
        return jsonify({"error": "재료 이름, 수량, 유통기한은 필수입니다."}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # Ingredients 테이블에서 재료 ID를 찾거나 새로 추가
        cursor.execute("SELECT ingredient_id FROM Ingredients WHERE ingredient_name = ?", (ingredient_name,))
        ingredient_result = cursor.fetchone()
        ingredient_id = None
        if ingredient_result:
            ingredient_id = ingredient_result['ingredient_id']
        else:
            # 재료가 없으면 Ingredients 테이블에 새 재료 추가 (기본 카테고리/단위는 필요시 추가 입력)
            cursor.execute("INSERT INTO Ingredients (ingredient_name) VALUES (?)", (ingredient_name,))
            ingredient_id = cursor.lastrowid
            conn.commit() # Ingredients 테이블에 추가된 내용 커밋

        if not ingredient_id:
             return jsonify({"error": "재료 ID를 가져오거나 생성할 수 없습니다."}), 500

        # User_Ingredients 테이블에 추가
        sql = """
            INSERT INTO User_Ingredients (user_id, ingredient_id, quantity, purchase_date, expiration_date, location)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(sql, (current_user_id, ingredient_id, quantity, purchase_date, expiration_date, location))
        conn.commit()
        return jsonify({"message": "재료가 성공적으로 추가되었습니다.", "user_ingredient_id": cursor.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        print(f"재료 추가 오류: {e}")
        return jsonify({"error": f"재료 추가 오류: {e}"}), 500
    finally:
        conn.close()

@app.route('/api/user_ingredients/<int:user_ingredient_id>', methods=['PUT'])
@token_required
def update_user_ingredient(current_user_id, user_ingredient_id):
    """사용자 보유 재료 정보를 업데이트합니다."""
    data = request.json
    quantity = data.get('quantity')
    purchase_date = data.get('purchase_date')
    expiration_date = data.get('expiration_date')
    location = data.get('location')

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # 해당 재료가 현재 사용자 소유인지 확인
        cursor.execute("SELECT user_id FROM User_Ingredients WHERE user_ingredient_id = ?", (user_ingredient_id,))
        result = cursor.fetchone()
        if not result or result['user_id'] != current_user_id:
            return jsonify({"error": "권한이 없습니다."}), 403

        update_fields = []
        update_values = []
        if quantity is not None:
            update_fields.append("quantity = ?")
            update_values.append(quantity)
        if purchase_date is not None:
            update_fields.append("purchase_date = ?")
            update_values.append(purchase_date)
        if expiration_date is not None:
            update_fields.append("expiration_date = ?")
            update_values.append(expiration_date)
        if location is not None:
            update_fields.append("location = ?")
            update_values.append(location)

        if not update_fields:
            return jsonify({"message": "업데이트할 내용이 없습니다."}), 200

        sql = f"UPDATE User_Ingredients SET {', '.join(update_fields)} WHERE user_ingredient_id = ?"
        update_values.append(user_ingredient_id)
        cursor.execute(sql, tuple(update_values))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"message": "해당 재료를 찾을 수 없거나 변경된 내용이 없습니다."}), 404
        return jsonify({"message": "재료 정보가 성공적으로 업데이트되었습니다."}), 200
    except Exception as e:
        conn.rollback()
        print(f"재료 업데이트 오류: {e}")
        return jsonify({"error": f"재료 업데이트 오류: {e}"}), 500
    finally:
        conn.close()

@app.route('/api/user_ingredients/<int:user_ingredient_id>', methods=['DELETE'])
@token_required
def delete_user_ingredient(current_user_id, user_ingredient_id):
    """사용자 보유 재료를 삭제합니다."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # 해당 재료가 현재 사용자 소유인지 확인
        cursor.execute("SELECT user_id FROM User_Ingredients WHERE user_ingredient_id = ?", (user_ingredient_id,))
        result = cursor.fetchone()
        if not result or result['user_id'] != current_user_id:
            return jsonify({"error": "권한이 없습니다."}), 403

        sql = "DELETE FROM User_Ingredients WHERE user_ingredient_id = ?"
        cursor.execute(sql, (user_ingredient_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"message": "해당 재료를 찾을 수 없습니다."}), 404
        return jsonify({"message": "재료가 성공적으로 삭제되었습니다."}), 200
    except Exception as e:
        conn.rollback()
        print(f"재료 삭제 오류: {e}")
        return jsonify({"error": f"재료 삭제 오류: {e}"}), 500
    finally:
        conn.close()

# --- 3. 레시피 추천 API (OpenAI 연동) ---
@app.route('/api/recommend_recipes', methods=['POST'])
@token_required
def recommend_recipes(current_user_id):
    """
    현재 로그인한 사용자의 보유 재료를 기반으로 OpenAI GPT 모델을 통해 레시피를 추천합니다.
    요청 형식: (재료는 자동으로 DB에서 가져옴)
    {
        "allergies": ["땅콩"],
        "preferences": ["매운맛", "간단한 요리"]
    }
    """
    data = request.json
    user_allergies = data.get('allergies', [])
    user_preferences = data.get('preferences', [])

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # 1. 사용자의 보유 재료 조회
        cursor.execute("""
            SELECT i.ingredient_name
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            WHERE ui.user_id = ?
        """, (current_user_id,))
        user_ingredients_raw = cursor.fetchall()
        user_ingredients = [ing['ingredient_name'] for ing in user_ingredients_raw]

        if not user_ingredients:
            return jsonify({"message": "보유 재료가 없으면 레시피 추천이 어렵습니다. 재료를 먼저 추가해주세요."}), 200

        ingredients_str = ", ".join(user_ingredients)

        # 2. 사용자의 알레르기 및 선호도 조회 (Users 테이블에서 가져올 수도 있음)
        # 여기서는 요청 바디에서 직접 받는 것으로 구현
        # 실제 구현 시 Users 테이블의 allergy_info, preferences 컬럼을 활용할 수 있습니다.
        allergy_str = f"알레르기가 있다면 다음 재료는 피해주세요: {', '.join(user_allergies)}." if user_allergies else ""
        preference_str = f"다음 선호도를 고려해주세요: {', '.join(user_preferences)}." if user_preferences else ""

        # 재료별 상세 정보 수집
        cursor.execute("""
            SELECT i.ingredient_name, ui.quantity, ui.expiration_date, ui.location, i.unit
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            WHERE ui.user_id = ?
            ORDER BY ui.expiration_date ASC
        """, (current_user_id,))
        
        detailed_ingredients = cursor.fetchall()
        ingredient_details = []
        
        for ing in detailed_ingredients:
            exp_date = datetime.strptime(ing['expiration_date'], '%Y-%m-%d')
            days_left = (exp_date - datetime.now()).days
            urgency = "🔴 곧 만료" if days_left <= 2 else "🟡 주의" if days_left <= 5 else "🟢 신선함"
            
            ingredient_details.append(f"{ing['ingredient_name']} ({ing['quantity']}{ing['unit'] or '개'}, {urgency})")

        # 3. 강화된 OpenAI GPT 프롬프트
        system_prompt = """당신은 미슐랭 스타 셰프이자 영양 전문가입니다. 
        사용자의 냉장고 재료를 최대한 활용하여 맛있고 영양가 있는 레시피를 추천해주세요.
        
        응답 형식:
        🍳 **레시피 제목**
        ⏰ 조리시간: X분
        👥 인분: X인분
        🌟 난이도: 쉬움/보통/어려움
        
        📋 **주재료 (보유중)**
        - 재료명: 사용량
        
        🛒 **추가 필요 재료** (선택사항)
        - 재료명: 사용량 (대체 가능한 재료도 제시)
        
        👨‍🍳 **조리법**
        1. 단계별 상세 설명
        2. 요리 팁과 주의사항 포함
        
        💡 **셰프의 팁**
        - 맛을 더하는 비법이나 변형 방법
        
        ═══════════════════════════
        
        한국인의 입맛에 맞는 현실적이고 실용적인 레시피를 제공해주세요."""
        
        user_prompt = f"""
        🥘 **현재 보유 재료:**
        {chr(10).join(ingredient_details)}
        
        🚫 **알레르기:** {', '.join(user_allergies) if user_allergies else '없음'}
        ❤️ **선호사항:** {', '.join(user_preferences) if user_preferences else '없음'}
        
        위 재료들을 최대한 활용하여 3가지 다양한 요리를 추천해주세요. 
        만료 임박 재료(🔴, 🟡)를 우선적으로 사용하는 레시피를 포함해주세요.
        """

        prompt_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        ai_response = client.chat.completions.create(
            model=OPENAI_MODEL,  # GPT-4o-mini 사용 (가성비 최고!)
            messages=prompt_messages,
            max_tokens=1200,  # 더 상세한 응답을 위해 증가
            temperature=0.8   # 창의성 약간 증가
        )

        ai_recommendation_text = ai_response.choices[0].message.content.strip()

        # TODO: AI 추천 텍스트를 파싱하여 개별 레시피 객체로 분리하고,
        # TODO: 필요한 경우 DB에 레시피를 저장하거나, 기존 레시피와 매칭하는 로직 추가
        # TODO: 부족한 재료를 식별하여 쇼핑 리스트에 추가하는 로직도 여기에 포함될 수 있습니다.
        # 이 부분은 AI 응답의 구조에 따라 복잡해질 수 있으므로, 별도의 파싱 함수가 필요합니다.

        return jsonify({
            "status": "success",
            "recommended_recipes_text": ai_recommendation_text,
            "user_ingredients": user_ingredients
        })

    except openai.AuthenticationError as e:
        print(f"OpenAI API 인증 오류: {e}")
        return jsonify({"error": "OpenAI API 키가 유효하지 않습니다. API 키를 확인해주세요."}), 401
    except openai.RateLimitError as e:
        print(f"OpenAI API 사용량 초과: {e}")
        return jsonify({"error": "API 사용량이 초과되었습니다. 잠시 후 다시 시도해주세요."}), 429
    except openai.APIError as e:
        print(f"OpenAI API 오류 발생: {e}")
        return jsonify({"error": f"OpenAI API 오류: {str(e)}"}), 500
    except Exception as e:
        print(f"서버 오류 발생: {e}")
        return jsonify({"error": f"서버 내부 오류: {e}"}), 500
    finally:
        conn.close()

# --- 4. 시각화 및 분석 API (OpenAI 활용) ---
@app.route('/api/dashboard-stats', methods=['GET'])
@token_required
def get_dashboard_stats(current_user_id):
    """대시보드용 통계 데이터를 조회합니다."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        
        # 재료 수
        cursor.execute("SELECT COUNT(*) as count FROM User_Ingredients WHERE user_id = ?", (current_user_id,))
        ingredient_count = cursor.fetchone()['count']
        
        # 카테고리별 재료 분포
        cursor.execute("""
            SELECT i.category, COUNT(*) as count
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            WHERE ui.user_id = ? AND i.category IS NOT NULL
            GROUP BY i.category
        """, (current_user_id,))
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
            WHERE user_id = ?
            GROUP BY status
        """, (current_user_id,))
        expiration_status = [dict(row) for row in cursor.fetchall()]
        
        # 위치별 재료 분포
        cursor.execute("""
            SELECT location, COUNT(*) as count
            FROM User_Ingredients 
            WHERE user_id = ? AND location IS NOT NULL
            GROUP BY location
        """, (current_user_id,))
        location_distribution = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            "status": "success",
            "stats": {
                "ingredient_count": ingredient_count,
                "category_distribution": category_distribution,
                "expiration_status": expiration_status,
                "location_distribution": location_distribution
            }
        })
    except Exception as e:
        print(f"통계 조회 오류: {e}")
        return jsonify({"error": f"통계 조회 오류: {e}"}), 500
    finally:
        conn.close()

@app.route('/api/generate-chart-description', methods=['POST'])
@token_required
def generate_chart_description(current_user_id):
    """GPT-4o-mini를 사용하여 차트 데이터를 텍스트로 분석하고 설명합니다."""
    data = request.json
    chart_type = data.get('chart_type')  # 'category', 'expiration', 'location'
    chart_data = data.get('chart_data')
    
    if not chart_type or not chart_data:
        return jsonify({"error": "차트 타입과 데이터가 필요합니다."}), 400
    
    try:
        # 차트 데이터를 텍스트로 변환
        if chart_type == 'category':
            data_text = ", ".join([f"{item['category']}: {item['count']}개" for item in chart_data])
            chart_title = "카테고리별 재료 분포"
        elif chart_type == 'expiration':
            data_text = ", ".join([f"{item['status']}: {item['count']}개" for item in chart_data])
            chart_title = "유통기한 현황"
        elif chart_type == 'location':
            data_text = ", ".join([f"{item['location']}: {item['count']}개" for item in chart_data])
            chart_title = "보관 위치별 분포"
        else:
            return jsonify({"error": "지원하지 않는 차트 타입입니다."}), 400
        
        system_prompt = """당신은 데이터 분석 전문가입니다. 
        주어진 데이터를 분석하여 시각적으로 이해하기 쉬운 설명과 인사이트를 제공해주세요."""
        
        user_prompt = f"""
        📊 **{chart_title}**
        데이터: {data_text}
        
        다음 형식으로 분석해주세요:
        
        📈 **현황 요약**
        - 주요 특징과 패턴
        
        💡 **인사이트**
        - 데이터에서 발견되는 중요한 점들
        
        🎯 **추천사항**
        - 개선 방안이나 주의사항
        
        한국어로 친근하고 이해하기 쉽게 설명해주세요.
        """
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,  # GPT-4o-mini 사용 (가성비 최고!)
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=600,
            temperature=0.7
        )
        
        analysis = response.choices[0].message.content.strip()
        
        return jsonify({
            "status": "success",
            "chart_analysis": analysis,
            "chart_type": chart_type,
            "chart_title": chart_title,
            "data_summary": data_text
        })
        
    except Exception as e:
        print(f"차트 분석 오류: {e}")
        return jsonify({"error": f"차트 분석 오류: {e}"}), 500

@app.route('/api/analyze-nutrition', methods=['POST'])
@token_required
def analyze_nutrition(current_user_id):
    """GPT-4o-mini를 사용하여 영양 분석 및 건강 조언을 제공합니다."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # 사용자의 모든 재료 조회
        cursor.execute("""
            SELECT i.ingredient_name, i.category, ui.quantity, ui.expiration_date
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            WHERE ui.user_id = ?
        """, (current_user_id,))
        
        ingredients = cursor.fetchall()
        ingredients_list = [f"{ing['ingredient_name']} ({ing['quantity']}개, {ing['category'] or '기타'})" for ing in ingredients]
        
        system_prompt = """당신은 영양학 전문가이자 건강 컨설턴트입니다. 
        사용자의 보유 재료를 분석하여 영양학적 조언과 건강한 식단 제안을 해주세요."""
        
        user_prompt = f"""
        현재 보유 재료: {', '.join(ingredients_list)}
        
        다음 항목들을 분석해주세요:
        1. 영양소 균형 평가 (단백질, 탄수화물, 지방, 비타민, 미네랄)
        2. 부족한 영양소와 추천 재료
        3. 건강한 식단 구성 제안
        4. 주의사항 및 개선점
        
        한국어로 친근하고 이해하기 쉽게 설명해주세요.
        """
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,  # GPT-4o-mini 사용 (가성비 최고!)
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        analysis = response.choices[0].message.content.strip()
        
        return jsonify({
            "status": "success",
            "nutrition_analysis": analysis,
            "ingredient_count": len(ingredients)
        })
        
    except Exception as e:
        print(f"영양 분석 오류: {e}")
        return jsonify({"error": f"영양 분석 오류: {e}"}), 500
    finally:
        conn.close()

@app.route('/api/generate-meal-plan', methods=['POST'])
@token_required
def generate_meal_plan(current_user_id):
    """GPT-4o-mini를 사용하여 주간 식단 계획을 생성합니다."""
    data = request.json
    days = data.get('days', 7)  # 기본 7일
    preferences = data.get('preferences', [])
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # 사용자의 재료 조회
        cursor.execute("""
            SELECT i.ingredient_name, ui.quantity, ui.expiration_date
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            WHERE ui.user_id = ?
            ORDER BY ui.expiration_date ASC
        """, (current_user_id,))
        
        ingredients = cursor.fetchall()
        ingredients_text = []
        
        for ing in ingredients:
            exp_date = datetime.strptime(ing['expiration_date'], '%Y-%m-%d')
            days_left = (exp_date - datetime.now()).days
            urgency = "🔴" if days_left <= 2 else "🟡" if days_left <= 5 else "🟢"
            ingredients_text.append(f"{ing['ingredient_name']} ({ing['quantity']}개, {urgency})")
        
        system_prompt = """당신은 전문 영양사이자 요리 전문가입니다. 
        사용자의 보유 재료를 최대한 활용하여 균형 잡힌 주간 식단을 계획해주세요."""
        
        user_prompt = f"""
        보유 재료: {', '.join(ingredients_text)}
        선호사항: {', '.join(preferences) if preferences else '없음'}
        기간: {days}일
        
        다음 형식으로 식단을 작성해주세요:
        
        📅 **1일차**
        🌅 아침: 메뉴명 (사용 재료)
        🌞 점심: 메뉴명 (사용 재료)  
        🌙 저녁: 메뉴명 (사용 재료)
        
        - 만료 임박 재료(🔴, 🟡)를 우선 사용
        - 영양 균형 고려
        - 한국인 입맛에 맞는 현실적인 메뉴
        - 간단한 조리법 포함
        """
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,  # GPT-4o-mini 사용 (가성비 최고!)
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500,
            temperature=0.8
        )
        
        meal_plan = response.choices[0].message.content.strip()
        
        return jsonify({
            "status": "success",
            "meal_plan": meal_plan,
            "days": days,
            "ingredients_used": len(ingredients)
        })
        
    except Exception as e:
        print(f"식단 계획 생성 오류: {e}")
        return jsonify({"error": f"식단 계획 생성 오류: {e}"}), 500
    finally:
        conn.close()

@app.route('/api/price-analysis', methods=['GET'])
@token_required
def get_price_analysis(current_user_id):
    """GPT-4o-mini를 사용하여 가격 분석 및 절약 팁을 제공합니다."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # 사용자의 재료 및 구매 정보 조회
        cursor.execute("""
            SELECT i.ingredient_name, i.category, ui.quantity, ui.purchase_date, ui.expiration_date
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            WHERE ui.user_id = ?
        """, (current_user_id,))
        
        ingredients = cursor.fetchall()
        
        # 카테고리별 분석을 위한 데이터 정리
        category_data = {}
        expired_items = []
        
        for ing in ingredients:
            category = ing['category'] or '기타'
            if category not in category_data:
                category_data[category] = []
            category_data[category].append(ing['ingredient_name'])
            
            # 만료된 재료 확인
            exp_date = datetime.strptime(ing['expiration_date'], '%Y-%m-%d')
            if exp_date < datetime.now():
                expired_items.append(ing['ingredient_name'])
        
        system_prompt = """당신은 가정경제 전문가이자 식품 구매 컨설턴트입니다. 
        사용자의 식재료 현황을 분석하여 경제적인 조언을 해주세요."""
        
        analysis_text = f"""
        보유 재료 현황:
        {chr(10).join([f"- {cat}: {', '.join(items)}" for cat, items in category_data.items()])}
        
        만료된 재료: {', '.join(expired_items) if expired_items else '없음'}
        총 재료 수: {len(ingredients)}개
        """
        
        user_prompt = f"""
        {analysis_text}
        
        다음 항목들을 분석해주세요:
        1. 💰 현재 재료 활용도 평가
        2. 🗑️ 식품 낭비 현황 및 개선 방안
        3. 💡 경제적인 구매 전략
        4. 📊 카테고리별 균형 분석
        5. 🎯 절약 팁 및 추천사항
        
        구체적이고 실용적인 조언을 한국어로 제공해주세요.
        """
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,  # GPT-4o-mini 사용 (가성비 최고!)
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        analysis = response.choices[0].message.content.strip()
        
        return jsonify({
            "status": "success",
            "price_analysis": analysis,
            "expired_count": len(expired_items),
            "total_ingredients": len(ingredients),
            "categories": list(category_data.keys())
        })
        
    except Exception as e:
        print(f"가격 분석 오류: {e}")
        return jsonify({"error": f"가격 분석 오류: {e}"}), 500
    finally:
        conn.close()

# --- 5. 레시피 관리 API (예시) ---
@app.route('/api/recipes', methods=['POST'])
@token_required
def add_recipe(current_user_id):
    """새로운 레시피를 추가합니다."""
    data = request.json
    recipe_name = data.get('recipe_name')
    instructions = data.get('instructions')
    ingredients_list = data.get('ingredients', []) # [{'name': '양파', 'quantity': 1, 'unit': '개'}]

    if not all([recipe_name, instructions, ingredients_list]):
        return jsonify({"error": "레시피 이름, 조리법, 재료 목록은 필수입니다."}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # Recipes 테이블에 레시피 추가
        sql_recipe = """
            INSERT INTO Recipes (recipe_name, instructions, created_by)
            VALUES (?, ?, ?)
        """
        cursor.execute(sql_recipe, (recipe_name, instructions, current_user_id))
        recipe_id = cursor.lastrowid

        # Recipe_Ingredients 테이블에 재료 정보 추가
        for ing_data in ingredients_list:
            ing_name = ing_data.get('name')
            ing_quantity = ing_data.get('quantity')
            ing_unit = ing_data.get('unit')

            if not all([ing_name, ing_quantity]):
                continue # 유효하지 않은 재료는 건너뛰기

            # Ingredients 테이블에서 재료 ID 찾기 또는 추가
            cursor.execute("SELECT ingredient_id FROM Ingredients WHERE ingredient_name = ?", (ing_name,))
            ingredient_result = cursor.fetchone()
            ingredient_id = None
            if ingredient_result:
                ingredient_id = ingredient_result['ingredient_id']
            else:
                cursor.execute("INSERT INTO Ingredients (ingredient_name) VALUES (?)", (ing_name,))
                ingredient_id = cursor.lastrowid
                conn.commit() # Ingredients 테이블에 추가된 내용 커밋

            if ingredient_id:
                sql_recipe_ing = """
                    INSERT INTO Recipe_Ingredients (recipe_id, ingredient_id, quantity_needed, unit)
                    VALUES (?, ?, ?, ?)
                """
                cursor.execute(sql_recipe_ing, (recipe_id, ingredient_id, ing_quantity, ing_unit))
        conn.commit()
        return jsonify({"message": "레시피가 성공적으로 추가되었습니다.", "recipe_id": recipe_id}), 201
    except Exception as e:
        conn.rollback()
        print(f"레시피 추가 오류: {e}")
        return jsonify({"error": f"레시피 추가 오류: {e}"}), 500
    finally:
        conn.close()

@app.route('/api/recipes/<int:recipe_id>', methods=['GET'])
def get_recipe_detail(recipe_id):
    """특정 레시피의 상세 정보를 조회합니다."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # 레시피 기본 정보 조회
        cursor.execute("SELECT * FROM Recipes WHERE recipe_id = ?", (recipe_id,))
        recipe = cursor.fetchone()
        if not recipe:
            return jsonify({"message": "해당 레시피를 찾을 수 없습니다."}), 404

        # 레시피 재료 정보 조회
        cursor.execute("""
            SELECT ri.quantity_needed, ri.unit, i.ingredient_name
            FROM Recipe_Ingredients ri
            JOIN Ingredients i ON ri.ingredient_id = i.ingredient_id
            WHERE ri.recipe_id = ?
        """, (recipe_id,))
        ingredients = cursor.fetchall()
        
        recipe_dict = dict(recipe)
        recipe_dict['ingredients'] = [dict(row) for row in ingredients]

        return jsonify({"status": "success", "recipe": recipe_dict})
    except Exception as e:
        print(f"레시피 조회 오류: {e}")
        return jsonify({"error": f"레시피 조회 오류: {e}"}), 500
    finally:
        conn.close()

# --- 6. 스마트 재료 추천 API ---


# --- 애플리케이션 실행 ---
def init_db():
    """데이터베이스 테이블을 초기화합니다."""
    conn = None
    try:
        conn = sqlite3.connect('recipe_management.db')
        cursor = conn.cursor()
        
        # 기존 테이블 삭제 (구조 변경을 위해)
        cursor.execute('DROP TABLE IF EXISTS Recipe_Ingredients')
        cursor.execute('DROP TABLE IF EXISTS User_Ingredients')
        cursor.execute('DROP TABLE IF EXISTS Recipes')
        cursor.execute('DROP TABLE IF EXISTS Ingredients')
        cursor.execute('DROP TABLE IF EXISTS Users')
        
        # Users 테이블 생성 (password_hash 필드 사용)
        cursor.execute('''
            CREATE TABLE Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                allergy_info TEXT,
                preferences TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Ingredients 테이블 생성
        cursor.execute('''
            CREATE TABLE Ingredients (
                ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_name TEXT NOT NULL UNIQUE,
                category TEXT,
                unit TEXT,
                image_url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User_Ingredients 테이블 생성
        cursor.execute('''
            CREATE TABLE User_Ingredients (
                user_ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                purchase_date DATE,
                expiration_date DATE,
                location TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id),
                FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id)
            )
        ''')
        
        # Recipes 테이블 생성
        cursor.execute('''
            CREATE TABLE Recipes (
                recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_name TEXT NOT NULL,
                instructions TEXT NOT NULL,
                created_by INTEGER,
                cooking_time INTEGER,
                difficulty_level TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES Users(user_id)
            )
        ''')
        
        # Recipe_Ingredients 테이블 생성
        cursor.execute('''
            CREATE TABLE Recipe_Ingredients (
                recipe_ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantity_needed REAL NOT NULL,
                unit TEXT,
                FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id),
                FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id)
            )
        ''')
        
        conn.commit()
        print("데이터베이스 테이블 초기화 완료")
    except Exception as e:
        print(f"데이터베이스 초기화 오류: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# --- 샘플 데이터 생성 함수 ---
def create_sample_data():
    """샘플 사용자와 재료 데이터를 생성합니다."""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 샘플 사용자 생성
        sample_users = [
            {
                'username': 'demo_user',
                'email': 'demo@example.com',
                'password': 'demo123',
                'allergy_info': '땅콩, 갑각류',
                'preferences': '매운맛, 간단한 요리'
            },
            {
                'username': 'chef_kim',
                'email': 'chef@example.com', 
                'password': 'chef123',
                'allergy_info': '',
                'preferences': '한식, 건강식'
            },
            {
                'username': '1',
                'email': 'user1@example.com',
                'password': '1103',
                'allergy_info': '',
                'preferences': '한식, 집밥, 간편요리'
            }
        ]
        
        user_ids = []
        for user_data in sample_users:
            # 이미 존재하는지 확인
            cursor.execute("SELECT user_id FROM Users WHERE username = ?", (user_data['username'],))
            existing_user = cursor.fetchone()
            
            if not existing_user:
                password_hash = generate_password_hash(user_data['password'])
                cursor.execute("""
                    INSERT INTO Users (username, email, password_hash, allergy_info, preferences)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_data['username'], user_data['email'], password_hash, 
                     user_data['allergy_info'], user_data['preferences']))
                user_ids.append(cursor.lastrowid)
            else:
                user_ids.append(existing_user['user_id'])
        
        # 기본 재료 데이터
        sample_ingredients = [
            {'name': '양파', 'category': '채소', 'unit': '개'},
            {'name': '당근', 'category': '채소', 'unit': '개'},
            {'name': '감자', 'category': '채소', 'unit': '개'},
            {'name': '대파', 'category': '채소', 'unit': '대'},
            {'name': '마늘', 'category': '향신료', 'unit': '쪽'},
            {'name': '생강', 'category': '향신료', 'unit': 'g'},
            {'name': '닭가슴살', 'category': '육류', 'unit': 'g'},
            {'name': '돼지고기', 'category': '육류', 'unit': 'g'},
            {'name': '쇠고기', 'category': '육류', 'unit': 'g'},
            {'name': '계란', 'category': '유제품', 'unit': '개'},
            {'name': '우유', 'category': '유제품', 'unit': 'ml'},
            {'name': '쌀', 'category': '곡물', 'unit': 'g'},
            {'name': '김치', 'category': '발효식품', 'unit': 'g'},
            {'name': '두부', 'category': '콩제품', 'unit': '모'},
            {'name': '버섯', 'category': '채소', 'unit': 'g'},
            {'name': '토마토', 'category': '채소', 'unit': '개'},
            {'name': '오이', 'category': '채소', 'unit': '개'},
            {'name': '상추', 'category': '채소', 'unit': 'g'},
            {'name': '고추', 'category': '채소', 'unit': '개'},
            {'name': '파프리카', 'category': '채소', 'unit': '개'}
        ]
        
        ingredient_ids = {}
        for ing_data in sample_ingredients:
            cursor.execute("SELECT ingredient_id FROM Ingredients WHERE ingredient_name = ?", (ing_data['name'],))
            existing_ing = cursor.fetchone()
            
            if not existing_ing:
                cursor.execute("""
                    INSERT INTO Ingredients (ingredient_name, category, unit)
                    VALUES (?, ?, ?)
                """, (ing_data['name'], ing_data['category'], ing_data['unit']))
                ingredient_ids[ing_data['name']] = cursor.lastrowid
            else:
                ingredient_ids[ing_data['name']] = existing_ing['ingredient_id']
        
        # 사용자들에게 샘플 재료 추가
        if user_ids:
            # 각 사용자별 샘플 재료 정의
            user_ingredients_data = {
                0: [  # demo_user
                    {'name': '양파', 'quantity': 3, 'location': '냉장실', 'days_until_expiry': 7},
                    {'name': '당근', 'quantity': 2, 'location': '냉장실', 'days_until_expiry': 10},
                    {'name': '감자', 'quantity': 5, 'location': '상온', 'days_until_expiry': 14},
                    {'name': '닭가슴살', 'quantity': 500, 'location': '냉장실', 'days_until_expiry': 3},
                    {'name': '계란', 'quantity': 12, 'location': '냉장실', 'days_until_expiry': 14},
                    {'name': '쌀', 'quantity': 2000, 'location': '상온', 'days_until_expiry': 365},
                    {'name': '김치', 'quantity': 300, 'location': '냉장실', 'days_until_expiry': 30},
                    {'name': '두부', 'quantity': 1, 'location': '냉장실', 'days_until_expiry': 5},
                    {'name': '버섯', 'quantity': 200, 'location': '냉장실', 'days_until_expiry': 4},
                    {'name': '대파', 'quantity': 2, 'location': '냉장실', 'days_until_expiry': 7}
                ],
                2: [  # 사용자 '1' (세 번째 사용자)
                    {'name': '양파', 'quantity': 4, 'location': '냉장실', 'days_until_expiry': 8},
                    {'name': '당근', 'quantity': 3, 'location': '냉장실', 'days_until_expiry': 12},
                    {'name': '감자', 'quantity': 6, 'location': '상온', 'days_until_expiry': 20},
                    {'name': '마늘', 'quantity': 10, 'location': '냉장실', 'days_until_expiry': 15},
                    {'name': '생강', 'quantity': 50, 'location': '냉장실', 'days_until_expiry': 10},
                    {'name': '돼지고기', 'quantity': 400, 'location': '냉장실', 'days_until_expiry': 2},
                    {'name': '계란', 'quantity': 10, 'location': '냉장실', 'days_until_expiry': 12},
                    {'name': '우유', 'quantity': 1000, 'location': '냉장실', 'days_until_expiry': 5},
                    {'name': '쌀', 'quantity': 3000, 'location': '상온', 'days_until_expiry': 365},
                    {'name': '김치', 'quantity': 500, 'location': '냉장실', 'days_until_expiry': 25},
                    {'name': '두부', 'quantity': 2, 'location': '냉장실', 'days_until_expiry': 4},
                    {'name': '토마토', 'quantity': 4, 'location': '냉장실', 'days_until_expiry': 6},
                    {'name': '오이', 'quantity': 3, 'location': '냉장실', 'days_until_expiry': 8},
                    {'name': '상추', 'quantity': 150, 'location': '냉장실', 'days_until_expiry': 3},
                    {'name': '파프리카', 'quantity': 2, 'location': '냉장실', 'days_until_expiry': 9}
                ]
            }
            
            # 각 사용자에게 재료 추가
            for user_index, sample_ingredients in user_ingredients_data.items():
                if user_index < len(user_ids):
                    user_id = user_ids[user_index]
                    
                    for user_ing in sample_ingredients:
                        # 이미 존재하는지 확인
                        cursor.execute("""
                            SELECT ui.user_ingredient_id FROM User_Ingredients ui
                            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
                            WHERE ui.user_id = ? AND i.ingredient_name = ?
                        """, (user_id, user_ing['name']))
                        
                        if not cursor.fetchone():
                            ingredient_id = ingredient_ids[user_ing['name']]
                            purchase_date = datetime.now().strftime('%Y-%m-%d')
                            expiration_date = (datetime.now() + timedelta(days=user_ing['days_until_expiry'])).strftime('%Y-%m-%d')
                            
                            cursor.execute("""
                                INSERT INTO User_Ingredients (user_id, ingredient_id, quantity, purchase_date, expiration_date, location)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (user_id, ingredient_id, user_ing['quantity'], purchase_date, expiration_date, user_ing['location']))
        
        conn.commit()
        print("✅ 샘플 데이터 생성 완료")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 샘플 데이터 생성 오류: {e}")
        return False
    finally:
        conn.close()

# 샘플 데이터 생성 API
@app.route('/api/create-sample-data', methods=['POST'])
def create_sample_data_api():
    """샘플 데이터를 생성합니다."""
    try:
        success = create_sample_data()
        if success:
            return jsonify({
                "message": "샘플 데이터가 성공적으로 생성되었습니다!",
                "demo_accounts": [
                    {
                        "username": "demo_user",
                        "password": "demo123",
                        "email": "demo@example.com",
                        "description": "기본 데모 계정"
                    },
                    {
                        "username": "1",
                        "password": "1103", 
                        "email": "user1@example.com",
                        "description": "사용자 맞춤 계정 (15가지 재료)"
                    }
                ]
            }), 200
        else:
            return jsonify({"error": "샘플 데이터 생성에 실패했습니다."}), 500
    except Exception as e:
        return jsonify({"error": f"샘플 데이터 생성 오류: {e}"}), 500

# GPT를 이용한 스마트 재료 추천 API
@app.route('/api/smart-ingredient-suggestions', methods=['POST'])
@token_required
def smart_ingredient_suggestions(current_user_id):
    """GPT를 이용해 사용자의 현재 재료를 기반으로 추가 구매할 재료를 추천합니다."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "데이터베이스 연결에 실패했습니다."}), 500

    try:
        cursor = conn.cursor()
        # 현재 사용자의 재료 조회
        cursor.execute("""
            SELECT i.ingredient_name, ui.quantity, ui.expiration_date, ui.location
            FROM User_Ingredients ui
            JOIN Ingredients i ON ui.ingredient_id = i.ingredient_id
            WHERE ui.user_id = ?
        """, (current_user_id,))
        
        current_ingredients = cursor.fetchall()
        ingredients_info = []
        
        for ing in current_ingredients:
            exp_date = datetime.strptime(ing['expiration_date'], '%Y-%m-%d')
            days_left = (exp_date - datetime.now()).days
            status = "신선함" if days_left > 3 else "곧 만료" if days_left > 0 else "만료됨"
            
            ingredients_info.append(f"{ing['ingredient_name']} ({ing['quantity']}{ing.get('unit', '개')}, {status})")
        
        if not ingredients_info:
            return jsonify({"message": "현재 보유 재료가 없습니다."}), 200
        
        # GPT에게 재료 추천 요청
        prompt_messages = [
            {
                "role": "system", 
                "content": "당신은 요리 전문가이자 영양사입니다. 사용자의 현재 냉장고 재료를 분석하여 균형잡힌 식단과 다양한 요리를 위해 추가로 구매하면 좋을 재료들을 추천해주세요. 한국 요리 문화를 고려하여 실용적이고 경제적인 추천을 해주세요."
            },
            {
                "role": "user", 
                "content": f"현재 제 냉장고에 있는 재료들입니다: {', '.join(ingredients_info)}. 이 재료들을 고려하여 추가로 구매하면 좋을 재료 5-7가지를 추천해주시고, 각각 왜 필요한지 간단히 설명해주세요."
            }
        ]
        
        ai_response = client.chat.completions.create(
            model=OPENAI_MODEL,  # GPT-4o-mini 사용 (가성비 최고!)
            messages=prompt_messages,
            max_tokens=500,
            temperature=0.7
        )
        
        suggestions = ai_response.choices[0].message.content.strip()
        
        return jsonify({
            "status": "success",
            "current_ingredients": len(current_ingredients),
            "suggestions": suggestions
        })
        
    except Exception as e:
        print(f"재료 추천 오류: {e}")
        return jsonify({"error": f"재료 추천 오류: {str(e)}"}), 500
    finally:
        conn.close()

# 데이터베이스 재설정 API 추가
@app.route('/api/reset-db', methods=['POST'])
def reset_database():
    """데이터베이스를 재설정합니다. (개발용)"""
    try:
        init_db()
        return jsonify({"message": "데이터베이스가 성공적으로 재설정되었습니다."}), 200
    except Exception as e:
        return jsonify({"error": f"데이터베이스 재설정 오류: {e}"}), 500

if __name__ == '__main__':
    print("🚀 레시피 관리 시스템 시작...")
    
    try:
        # 데이터베이스 파일이 없을 때만 초기화
        import os
        if not os.path.exists('recipe_management.db'):
            print("📦 데이터베이스 초기화 중...")
            init_db()
            print("✅ DB 초기화 완료")
            
            # 샘플 데이터 자동 생성
            print("� 샘플  데이터 생성 중...")
            create_sample_data()
        else:
            print("✅ 기존 데이터베이스 사용")
        
        print("🌟 서버 시작!")
        print("📍 브라우저에서 http://127.0.0.1:5000 접속")
        print("👤 데모 계정들:")
        print("   • demo_user / demo123 (기본 10가지 재료)")
        print("   • 1 / 1103 (맞춤 15가지 재료)")
        print("🛑 서버 중지: Ctrl+C")
        print("=" * 50)
        
        app.run(debug=True, port=5000, host='127.0.0.1')
    except Exception as e:
        print(f"❌ 서버 시작 오류: {e}")
        print("데이터베이스 파일을 삭제하고 다시 시도해보세요.")