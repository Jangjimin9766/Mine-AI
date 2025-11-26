import streamlit as st
import requests
import json

# FastAPI 서버 주소
API_URL = "http://localhost:8000/api/magazine/create"

st.set_page_config(page_title="M:ine AI Magazine Demo", page_icon="✨", layout="wide")

st.title("✨ M:ine AI Magazine Generator")
st.markdown("---")

# 사이드바 설정
with st.sidebar:
    st.header("Settings")
    topic = st.text_input("주제 (Topic)", placeholder="예: 2024 겨울 패션 트렌드")
    user_mood = st.text_input("사용자 무드 (선택)", placeholder="예: 시크, 모던")
    generate_btn = st.button("매거진 생성하기", type="primary")

if generate_btn and topic:
    with st.spinner("AI가 매거진을 열심히 만들고 있습니다... (약 10~20초 소요)"):
        try:
            payload = {"topic": topic}
            if user_mood:
                payload["user_mood"] = user_mood
            
            response = requests.post(API_URL, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                # --- 매거진 뷰어 ---
                st.success("매거진 생성 완료!")
                
                # 1. 헤더 섹션
                st.header(data.get("title", "제목 없음"))
                st.caption(f"Tags: {', '.join(data.get('tags', []))}")
                
                if data.get("cover_image_url"):
                    st.image(data["cover_image_url"], use_container_width=True)
                
                st.markdown(f"> **{data.get('introduction', '')}**")
                
                st.markdown("---")
                
                # 2. 본문 섹션들
                sections = data.get("sections", [])
                for section in sections:
                    st.subheader(section.get("heading", ""))
                    
                    col1, col2 = st.columns([1, 1])
                    
                    # 레이아웃 힌트에 따라 배치 다르게 (간단히 구현)
                    if section.get("image_url"):
                        with col1:
                            st.image(section["image_url"], use_container_width=True)
                        with col2:
                            st.write(section.get("content", ""))
                    else:
                        st.write(section.get("content", ""))
                    
                    st.markdown("<br>", unsafe_allow_html=True)

            else:
                st.error(f"생성 실패! 상태 코드: {response.status_code}")
                st.error(response.text)
                
        except Exception as e:
            st.error(f"에러 발생: {e}")

elif generate_btn and not topic:
    st.warning("주제를 입력해주세요!")

# 사용법 안내
st.sidebar.markdown("---")
st.sidebar.info(
    """
    **사용법**
    1. 주제를 입력하세요.
    2. '매거진 생성하기' 버튼을 누르세요.
    3. AI가 실시간으로 검색하고 작성한 매거진을 확인하세요.
    """
)
