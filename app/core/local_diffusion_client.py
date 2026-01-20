import torch
import sys

# Workaround for diffusers compatibility with PyTorch versions lacking torch.xpu
# (Intel XPU support). This MUST be before importing diffusers!
if not hasattr(torch, 'xpu'):
    class FakeXPU:
        """Complete mock of torch.xpu module for compatibility."""
        @staticmethod
        def is_available():
            return False
        @staticmethod
        def empty_cache():
            pass
        @staticmethod
        def synchronize():
            pass
        @staticmethod
        def device_count():
            return 0
        @staticmethod
        def current_device():
            return 0
        @staticmethod
        def get_device_name(device=None):
            return ""
        @staticmethod
        def manual_seed(seed):
            pass
        @staticmethod
        def manual_seed_all(seed):
            pass
        @staticmethod
        def set_device(device):
            pass
        @staticmethod
        def get_device_properties(device):
            return None
        @staticmethod  
        def memory_allocated(device=None):
            return 0
        @staticmethod
        def max_memory_allocated(device=None):
            return 0
    torch.xpu = FakeXPU()

# Now safe to import diffusers
from diffusers import DiffusionPipeline
import base64
from io import BytesIO

class LocalDiffusionClient:
    def __init__(self):
        self.pipe = None
        self.model_id = "stabilityai/stable-diffusion-xl-base-1.0"
        self.device = None
        self._load_attempted = False
        self._load_error = None
        # Lazy loading: 모델은 처음 요청이 들어올 때 로드합니다. (서버 시작 시간 단축)

    def _load_model(self) -> bool:
        """모델 로드. 성공 시 True, 실패 시 False 반환."""
        # 이미 로드 시도했으면 재시도 안 함 (에러 반복 방지)
        if self._load_attempted:
            return self.pipe is not None
        
        self._load_attempted = True
        
        # Device selection logic
        self.device = "cpu"
        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        
        print(f"⏳ Loading Stable Diffusion XL model to {self.device.upper()} (This may take a while on first run)...")
        try:
            self.pipe = DiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16,
                use_safetensors=True,
                variant="fp16"
            )
            
            self.pipe.to(self.device)
            
            # Optional: Memory optimization
            # self.pipe.enable_attention_slicing()
            
            print(f"✅ Model loaded successfully on {self.device.upper()}.")
            return True
        except Exception as e:
            self._load_error = str(e)
            print(f"❌ Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            self.pipe = None
            return False
    
    def is_ready(self) -> bool:
        """모델이 로드되어 준비된 상태인지 확인"""
        return self.pipe is not None
    
    def get_status(self) -> dict:
        """현재 상태 정보 반환"""
        return {
            "loaded": self.pipe is not None,
            "load_attempted": self._load_attempted,
            "device": self.device,
            "error": self._load_error
        }

    def generate_image(self, prompt: str) -> str:
        """
        Generate image using local Stable Diffusion XL.
        Returns: Data URI (Base64) on success, None on failure
        """
        if not self._load_model():
            print(f"⚠️ SDXL model not available. Status: {self.get_status()}")
            return None

        try:
            print(f"🎨 Generating image locally with prompt: {prompt[:50]}...")
            
            # Generate
            image = self.pipe(prompt=prompt, num_inference_steps=30).images[0]
            
            # Convert to Base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            print(f"✅ Image generated successfully")
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            print(f"❌ Local Generation Error: {e}")
            import traceback
            traceback.print_exc()
            return None


local_diffusion_client = LocalDiffusionClient()
