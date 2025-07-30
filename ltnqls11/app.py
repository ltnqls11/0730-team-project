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

# --- 환경 변수 설정 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY 환경 변수가 설정되지 않았습니다.")

# OpenAI 클라이언트 초기화 (새로운 방식)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

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
    return "레시피 관리 시스템 백엔드 API가 실행 중입니다."

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

        # 3. OpenAI GPT 모델에 프롬프트 전송
        prompt_messages = [
            {"role": "system", "content": "당신은 요리사로서 사용자의 냉장고 재료를 활용하여 맛있고 현실적인 레시피를 추천해주는 AI입니다. 레시피는 제목, 필요한 추가 재료(있다면), 조리법 순으로 간결하게 구성하고, 각 레시피 사이에는 구분선을 넣어주세요. 절대 사용자에게 부족한 재료를 직접적으로 언급하지 마세요. 한국어로 응답해주세요."},
            {"role": "user", "content": f"제가 현재 가지고 있는 재료는 다음과 같습니다: {ingredients_str}. 이 재료들로 만들 수 있는 요리 3가지 정도를 추천해주세요. {allergy_str} {preference_str} 각 레시피는 '제목:', '필요한 추가 재료:', '조리법:' 형태로 제공해주세요."}
        ]

        ai_response = client.chat.completions.create(
            model="gpt-3.5-turbo", # 또는 "gpt-4o", "gpt-4" 등 더 최신 모델 사용 가능
            messages=prompt_messages,
            max_tokens=800, # 응답 길이 제한
            temperature=0.7 # 창의성 조절 (0.0-1.0, 높을수록 창의적)
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

    except openai.APIError as e:
        print(f"OpenAI API 오류 발생: {e}")
        return jsonify({"error": f"OpenAI API 오류: {str(e)}"}), 500
    except Exception as e:
        print(f"서버 오류 발생: {e}")
        return jsonify({"error": f"서버 내부 오류: {e}"}), 500
    finally:
        conn.close()

# --- 4. 레시피 관리 API (예시) ---
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

# --- 애플리케이션 실행 ---
def init_db():
    """데이터베이스 테이블을 초기화합니다."""
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
    conn.close()
    print("데이터베이스 테이블 초기화 완료")

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
    init_db()
    print("DB 초기화 완료")
    app.run(debug=True, port=5000) # 개발 환경에서는 debug=True, 실제 배포 시에는 False