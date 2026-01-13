-- Supabase 설정 단계별 가이드

-- 1단계: 기존 테이블 확인
-- 다음 쿼리로 기존 테이블을 확인하세요:
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'ingredients', 'recipes', 'meal_plans');

-- 2단계: 기존 테이블 삭제 (필요시)
-- 테이블이 이미 존재한다면 다음 명령어를 실행하세요:
-- DROP TABLE IF EXISTS meal_plans CASCADE;
-- DROP TABLE IF EXISTS recipes CASCADE;
-- DROP TABLE IF EXISTS ingredients CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;

-- 3단계: 새 테이블 생성
-- database_schema.sql 파일의 내용을 실행하세요

-- 4단계: 테이블 생성 확인
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'ingredients', 'recipes', 'meal_plans')
ORDER BY table_name, ordinal_position;

-- 5단계: RLS 정책 확인
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies 
WHERE schemaname = 'public'
AND tablename IN ('users', 'ingredients', 'recipes', 'meal_plans'); 