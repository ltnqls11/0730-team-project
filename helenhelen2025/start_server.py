#!/usr/bin/env python3
"""
Flask 서버 시작 스크립트
"""

import subprocess
import sys
import os

def install_requirements():
    """필요한 패키지들을 설치합니다."""
    requirements = [
        'flask',
        'openai',
        'python-dotenv',
        'pyjwt'
    ]
    
    for package in requirements:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} 이미 설치됨")
        except ImportError:
            print(f"⚠ {package} 설치 중...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✓ {package} 설치 완료")

def check_env_file():
    """환경 변수 파일을 확인합니다."""
    if not os.path.exists('.env'):
        print("⚠ .env 파일이 없습니다. 생성 중...")
        with open('.env', 'w') as f:
            f.write('OPENAI_API_KEY=your_openai_api_key_here\n')
            f.write('JWT_SECRET_KEY=your_jwt_secret_key_here\n')
        print("✓ .env 파일이 생성되었습니다. API 키를 설정해주세요.")
    else:
        print("✓ .env 파일 존재")

def main():
    print("🚀 Flask 서버 시작 준비...")
    
    # 필요한 패키지 설치
    install_requirements()
    
    # 환경 변수 파일 확인
    check_env_file()
    
    print("\n🌟 Flask 서버를 시작합니다...")
    print("📍 서버 주소: http://127.0.0.1:5000")
    print("🛑 서버를 중지하려면 Ctrl+C를 누르세요\n")
    
    # Flask 서버 실행
    try:
        import app
        app.app.run(debug=True, port=5000, host='127.0.0.1')
    except KeyboardInterrupt:
        print("\n👋 서버가 중지되었습니다.")
    except Exception as e:
        print(f"❌ 서버 시작 오류: {e}")

if __name__ == '__main__':
    main()