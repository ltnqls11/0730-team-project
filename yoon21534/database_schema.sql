-- UUID 생성 확장 기능 활성화 (필요한 경우)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. profiles 테이블 (사용자 프로필 정보, auth.users와 연결)
-- Supabase Auth의 users 테이블과 1:1 관계를 가집니다.
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE, -- auth.users 테이블의 id를 참조
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS (Row Level Security) 활성화
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- 모든 사용자에게 자신의 프로필 조회 권한 부여
CREATE POLICY "Users can view their own profile" ON profiles
    FOR SELECT USING (auth.uid() = user_id);

-- 모든 사용자에게 자신의 프로필 생성 권한 부여 (회원가입 시)
CREATE POLICY "Users can insert their own profile" ON profiles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 모든 사용자에게 자신의 프로필 업데이트 권한 부여
CREATE POLICY "Users can update their own profile" ON profiles
    FOR UPDATE USING (auth.uid() = user_id);

-- 2. ingredients 테이블 (식재료 정보)
CREATE TABLE IF NOT EXISTS ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE, -- auth.users 테이블의 id를 참조
    name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT,
    purchase_date DATE,
    expiry_date DATE,
    category TEXT,
    location TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE ingredients ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own ingredients" ON ingredients
    FOR ALL USING (auth.uid() = user_id);

-- 3. recipes 테이블 (레시피 정보)
CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE, -- auth.users 테이블의 id를 참조
    name TEXT NOT NULL,
    description TEXT,
    ingredients_list TEXT, -- 쉼표로 구분된 재료 목록 또는 JSON 문자열
    cooking_time INT, -- 분 단위
    difficulty TEXT, -- 초급, 중급, 고급
    category TEXT, -- 한식, 양식 등
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE recipes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own recipes" ON recipes
    FOR ALL USING (auth.uid() = user_id);

-- 4. meal_plans 테이블 (식단 계획)
CREATE TABLE IF NOT EXISTS meal_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE, -- auth.users 테이블의 id를 참조
    recipe_id UUID REFERENCES public.recipes(id) ON DELETE SET NULL, -- recipes 테이블 참조
    plan_date DATE NOT NULL,
    meal_type TEXT NOT NULL, -- 아침, 점심, 저녁, 간식
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE meal_plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own meal plans" ON meal_plans
    FOR ALL USING (auth.uid() = user_id);

-- 5. shopping_list 테이블 (쇼핑 목록)
CREATE TABLE IF NOT EXISTS shopping_list (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE, -- auth.users 테이블의 id를 참조
    item_name TEXT NOT NULL,
    quantity REAL,
    unit TEXT,
    is_purchased BOOLEAN DEFAULT FALSE,
    priority TEXT DEFAULT '보통', -- 높음, 보통, 낮음
    added_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE shopping_list ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own shopping list" ON shopping_list
    FOR ALL USING (auth.uid() = user_id); 