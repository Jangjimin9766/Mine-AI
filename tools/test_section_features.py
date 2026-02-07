import sys
import os
import json
import asyncio

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from app.core.magazine_editor import analyze_user_intent, add_new_section, edit_section_content, regenerate_section
from tools.magazine_preview import save_preview

# Mock Data (현재 DB 연동 없이 로직 테스트용)
MOCK_MAGAZINE = {
    "id": 98,
    "title": "Rolex Daytona: 시간을 수집하는 완벽한 궤적",
    "subtitle": "모터스포츠의 심장부에서 탄생한 영원한 크로노그래프의 아이콘",
    "introduction": "롤렉스 코스모그래프 데이토나는 단순한 시계를 넘어 모터스포츠의 정밀함과 하이엔드 럭셔리의 정점을 상징합니다.",
    "cover_image_url": "https://images.unsplash.com/photo-1587836374828-4dbaba94cf0e?q=80&w=2070",
    "tags": ["브랜드", "철학", "기술적완성도", "롤렉스"],
    "sections": [
        {
            "id": 1,
            "heading": "데이토나의 기원: 속도와의 조우",
            "content": "<p>1963년, 롤렉스는 전문 카레이서들을 위해 코스모그래프 데이토나를 발표했습니다. 타키미터 베젤을 통해 평균 속도를 측정할 수 있는 이 기능적 도구는...</p>",
            "image_url": "https://images.unsplash.com/photo-1614164185128-e4ec99c436d7?q=80&w=1974",
            "layout_type": "basic",
            "layout_hint": "image_left",
            "caption": "정밀함의 상징, 데이토나 크로노그래프",
            "display_order": 0
        }
    ]
}

async def run_test():
    print("\n" + "="*50)
    print("💎 CIJ3 Section Feature Test Tool 💎")
    print("="*50)
    print("1. 섹션 추가 (Add Section)")
    print("2. 문단 추가 (Append Content to Section 1)")
    print("3. 전체 수정 (Full Rewrite Section 1)")
    print("4. 의도 분석 테스트 (Analyze Intent Only)")
    print("="*50)
    
    choice = input("원하시는 테스트 번호를 입력하세요: ")
    
    if choice == "1":
        msg = "데이토나의 투자 가치와 리셀 시장에 대한 섹션을 하나 더 추가해줘"
        print(f"\n🚀 실행: {msg}")
        new_section = add_new_section(MOCK_MAGAZINE, msg)
        MOCK_MAGAZINE["sections"].append(new_section)
        save_preview(MOCK_MAGAZINE, "test_cij3_added.html")
        print("\n✅ 결과 확인: test_cij3_added.html 파일을 열어보세요!")

    elif choice == "2":
        msg = "위 섹션에 폴 뉴먼 데이토나 경매 기록에 대한 구체적인 내용을 3문장 정도 덧붙여줘"
        print(f"\n🚀 실행: {msg}")
        # edit_section_content는 Spring 응답 형식을 따름
        result = edit_section_content(MOCK_MAGAZINE["sections"][0], msg, topic=MOCK_MAGAZINE["title"])
        if result["success"]:
            MOCK_MAGAZINE["sections"][0] = result["updated_section"]
            save_preview(MOCK_MAGAZINE, "test_cij3_appended.html")
            print("\n✅ 결과 확인: test_cij3_appended.html 파일을 열어보세요!")

    elif choice == "3":
        msg = "이 섹션을 더 시적이고 감성적인 톤으로 완전히 새로 써줘"
        print(f"\n🚀 실행: {msg}")
        new_section = regenerate_section(MOCK_MAGAZINE, 0, msg)
        MOCK_MAGAZINE["sections"][0] = new_section
        save_preview(MOCK_MAGAZINE, "test_cij3_rewritten.html")
        print("\n✅ 결과 확인: test_cij3_rewritten.html 파일을 열어보세요!")

    elif choice == "4":
        msg = input("\n분석하고 싶은 메시지를 입력하세요: ")
        intent = analyze_user_intent(msg, MOCK_MAGAZINE)
        print(f"\n🔍 분석 결과:")
        print(f"- 의도: {intent.action}")
        print(f"- 요지: {intent.instruction}")
        print(f"- 응답 메시지: {intent.response_message}")

if __name__ == "__main__":
    asyncio.run(run_test())
