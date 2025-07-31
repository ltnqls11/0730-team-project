from dotenv import load_dotenv
import os
from openai import OpenAI
import json

# 환경변수 로드
load_dotenv()

def test_openai_api():
    """OpenAI API 테스트 함수"""
    try:
        # API 키 확인
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            print("📝 .env 파일에 OPENAI_API_KEY=your_api_key_here 를 추가해주세요.")
            return False
        
        print("✅ API 키 확인 완료")
        
        # OpenAI 클라이언트 생성
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI 클라이언트 생성 완료")
        
        # 간단한 채팅 완료 API 테스트
        print("\n🤖 OpenAI API 테스트 중...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다."},
                {"role": "user", "content": "안녕하세요! 간단한 인사말을 해주세요."}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        print("✅ API 호출 성공!")
        print(f"📝 응답: {response.choices[0].message.content}")
        
        # 응답 정보 출력
        print(f"\n📊 응답 정보:")
        print(f"   - 모델: {response.model}")
        print(f"   - 사용된 토큰: {response.usage.total_tokens}")
        print(f"   - 프롬프트 토큰: {response.usage.prompt_tokens}")
        print(f"   - 완료 토큰: {response.usage.completion_tokens}")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 OpenAI API 테스트 시작\n")
    
    # 기본 채팅 완료 API 테스트
    print("=" * 50)
    print("1. 기본 Chat Completions API 테스트")
    print("=" * 50)
    chat_success = test_openai_api()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📋 테스트 결과 요약")
    print("=" * 50)
    print(f"Chat Completions API: {'✅ 성공' if chat_success else '❌ 실패'}")
    
    if chat_success:
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 위의 오류 메시지를 확인해주세요.")