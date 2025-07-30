# 한글 폰트 다운로드 및 설치 도구
import requests
import os
import streamlit as st

def download_nanum_font():
    """나눔고딕 폰트를 다운로드합니다."""
    font_url = "https://github.com/naver/nanumfont/raw/master/fonts/NanumGothic.ttf"
    font_path = "fonts/NanumGothic.ttf"
    
    # fonts 디렉토리 생성
    os.makedirs("fonts", exist_ok=True)
    
    if not os.path.exists(font_path):
        try:
            st.info("나눔고딕 폰트를 다운로드하는 중...")
            response = requests.get(font_url)
            response.raise_for_status()
            
            with open(font_path, 'wb') as f:
                f.write(response.content)
            
            st.success("✅ 나눔고딕 폰트 다운로드 완료!")
            return font_path
        except Exception as e:
            st.error(f"폰트 다운로드 실패: {e}")
            return None
    else:
        st.info("나눔고딕 폰트가 이미 존재합니다.")
        return font_path

if __name__ == "__main__":
    download_nanum_font()