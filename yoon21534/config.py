import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ornwsfdrkyuuduztqjmj.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ybndzZmRya3l1dWR1enRxam1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM4NTE5MjksImV4cCI6MjA2OTQyNzkyOX0.LoWlVmkDZ4RDGSa0mqaYgiFFhl91HRzQeyfYMTNfKQQ")

# 테스트 모드 (Supabase 연결 정보가 없을 때)
TEST_MODE = False  # 실제 연결 시도

# 데이터베이스 테이블명
INGREDIENTS_TABLE = "ingredients"
RECIPES_TABLE = "recipes"
MEAL_PLANS_TABLE = "meal_plans"
USERS_TABLE = "users" 