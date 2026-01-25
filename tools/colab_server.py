# =================================================================
# Mine-AI: Google Colab GPU Image Server (SDXL)
# =================================================================
# 이 코드를 Google Colab의 새 노트북 셀에 붙여넣고 실행하세요.
# 실행 전: [런타임] -> [런타임 유형 변경] -> [T4 GPU] 선택 확인

# 1. 필수 라이브러리 설치
!pip install -q fastapi uvicorn pyngrok pydantic diffusers transformers accelerator safetensors

import torch
from diffusers import DiffusionPipeline
from fastapi import FastAPI
from pydantic import BaseModel
import base64
from io import BytesIO
import uvicorn
from pyngrok import ngrok
import nest_asyncio

# 2. Stable Diffusion XL 모델 로드
print("⏳ Loading SDXL Model (this takes a few minutes)...")
pipe = DiffusionPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16,
    use_safetensors=True,
    variant="fp16"
)
pipe.to("cuda")
print("✅ Model Loaded on GPU!")

# 3. FastAPI 서버 설정
app = FastAPI()

class GenerateRequest(BaseModel):
    prompt: str

@app.post("/generate")
async def generate(req: GenerateRequest):
    print(f"🎨 Generating image for: {req.prompt[:50]}...")
    image = pipe(prompt=req.prompt, num_inference_steps=30).images[0]
    
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return {"image_url": f"data:image/png;base64,{img_str}"}

# 4. Ngrok 터널링 및 실행
# 사용자가 제공한 토큰으로 인증 설정
!ngrok config add-authtoken 38jPwLfZkU7IwoZXw3RUz86Lmze_6cY6R4yhWrYhb9iEvhJTZ

import threading

def run_server():
    print("\n🚀 Starting FastAPI server on port 8000...")
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    # Colab의 이벤트 루프와 충돌하지 않도록 스레드에서 실행
    server.run()

# 백그라운드 스레드에서 서버 시작
server_thread = threading.Thread(target=run_server)
server_thread.start()

print("\n🚀 Starting Public Tunnel...")
public_url = ngrok.connect(8000).public_url
print(f"\n====================================================")
print(f"🔗 COPY THIS URL: {public_url}/generate")
print(f"====================================================\n")
print("위 URL을 Mine-AI의 .env 파일 REMOTE_IMAGE_SERVER_URL에 넣으세요.")
print("서버가 백그라운드에서 실행 중입니다. (오류 메시지가 뜨더라도 위 URL이 나오면 성공입니다)")