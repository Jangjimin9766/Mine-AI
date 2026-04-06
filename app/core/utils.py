import re
from app.core.llm_client import llm_client

def is_mostly_english(text: str) -> bool:
    """
    Detects if the text contains more Latin characters than Korean characters.
    """
    if not text:
        return False
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    korean_chars = len(re.findall(r'[가-힣]', text))
    # If English characters dominate or no Korean is found, treat as likely English topic
    return english_chars > (korean_chars * 1.5)

def translate_to_korean(text: str, context: str = "magazine title") -> str:
    """
    Translates English text to professional Korean using LLM.
    """
    if not text:
        return text
    print(f"🌐 Translating {context} to Korean: {text[:50]}...")
    
    prompt = f"""
    Translate the following {context} into a natural, professional, and sophisticated Korean for a premium lifestyle magazine.
    Content: "{text}"
    
    [RULES]
    - Return ONLY the translated string.
    - Maintain the original meaning but enhance the phrasing to sound like a native Korean editor (잡지 에디터 톤).
    - Do not include any explanations or quotes.
    """
    
    res = llm_client.generate_text("You are a professional Korean magazine editor and translator.", prompt)
    return res.strip().strip('"').strip("'").strip()

def force_translate_magazine_json(data: dict) -> dict:
    """
    Traverses a magazine JSON and translates English fields to Korean.
    """
    if not data:
        return data
        
    # Translate Title
    if is_mostly_english(data.get('title')):
        data['title'] = translate_to_korean(data['title'], "magazine title")
        
    # Translate Sections
    for section in data.get('sections', []):
        if is_mostly_english(section.get('heading')):
            section['heading'] = translate_to_korean(section['heading'], "section heading")
            
        for para in section.get('paragraphs', []):
            if is_mostly_english(para.get('text')):
                para['text'] = translate_to_korean(para['text'], "paragraph body text")
                
    return data

def force_translate_section(section: dict) -> dict:
    """
    Translates a single section's English fields to Korean.
    """
    if not section:
        return section
        
    if is_mostly_english(section.get('heading')):
        section['heading'] = translate_to_korean(section['heading'], "section heading")
        
    for para in section.get('paragraphs', []):
        if is_mostly_english(para.get('subtitle')):
            para['subtitle'] = translate_to_korean(para['subtitle'], "paragraph subtitle")
        
        if is_mostly_english(para.get('text')):
            para['text'] = translate_to_korean(para['text'], "paragraph body text")
            
    return section
