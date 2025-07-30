# Supabase 설정 가이드

## 🚨 오류 해결: "relation 'users' already exists"

이 오류는 이미 테이블이 존재할 때 발생합니다. 다음 단계를 따라 해결하세요.

## 📋 단계별 설정

### 1단계: 기존 테이블 확인

Supabase SQL 편집기에서 다음 쿼리를 실행하여 기존 테이블을 확인하세요:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'ingredients', 'recipes', 'meal_plans');
```

### 2단계: 기존 테이블 삭제 (필요시)

테이블이 이미 존재한다면 다음 명령어를 실행하세요:

```sql
DROP TABLE IF EXISTS meal_plans CASCADE;
DROP TABLE IF EXISTS recipes CASCADE;
DROP TABLE IF EXISTS ingredients CASCADE;
DROP TABLE IF EXISTS users CASCADE;
```

### 3단계: 새 테이블 생성

`database_schema.sql` 파일의 내용을 Supabase SQL 편집기에서 실행하세요.

### 4단계: 테이블 생성 확인

다음 쿼리로 테이블이 올바르게 생성되었는지 확인하세요:

```sql
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'ingredients', 'recipes', 'meal_plans')
ORDER BY table_name, ordinal_position;
```

### 5단계: RLS 정책 확인

다음 쿼리로 RLS 정책이 올바르게 설정되었는지 확인하세요:

```sql
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
```

## 🔧 환경 변수 설정

### 1. Supabase 프로젝트 정보 확인

1. Supabase 대시보드에서 프로젝트 선택
2. Settings > API에서 다음 정보 확인:
   - Project URL
   - anon public key

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```
SUPABASE_URL=your_project_url_here
SUPABASE_KEY=your_anon_key_here
```

예시:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 🧪 테스트 모드

Supabase 연결 정보가 없거나 오류가 발생하면 애플리케이션이 자동으로 테스트 모드로 실행됩니다.

테스트 모드에서는:
- 모든 데이터가 메모리에 저장됩니다
- 애플리케이션을 재시작하면 데이터가 초기화됩니다
- 모든 기능을 테스트할 수 있습니다

## ✅ 확인 사항

1. **테이블 생성**: 4개의 테이블이 모두 생성되었는지 확인
2. **RLS 활성화**: 모든 테이블에 RLS가 활성화되었는지 확인
3. **정책 설정**: 각 테이블에 적절한 정책이 설정되었는지 확인
4. **환경 변수**: `.env` 파일에 올바른 Supabase 정보가 입력되었는지 확인

## 🚀 애플리케이션 실행

환경 변수를 설정한 후 애플리케이션을 재시작하세요:

```bash
streamlit run app.py
```

## 🔍 문제 해결

### 문제 1: "supabase_url is required" 오류
- `.env` 파일이 올바른 위치에 있는지 확인
- 환경 변수 이름이 정확한지 확인

### 문제 2: "relation already exists" 오류
- 위의 2단계에서 기존 테이블을 삭제하세요

### 문제 3: RLS 정책 오류
- `setup_supabase.sql` 파일의 5단계를 실행하여 정책을 확인하세요

### 문제 4: 연결 오류
- Supabase 프로젝트가 활성 상태인지 확인
- API 키가 올바른지 확인
- 네트워크 연결을 확인

## 📞 지원

문제가 지속되면 다음을 확인하세요:
1. Supabase 프로젝트 상태
2. API 키 권한
3. 네트워크 연결
4. 방화벽 설정 