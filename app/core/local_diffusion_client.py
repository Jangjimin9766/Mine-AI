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
    torch.xpu = FakeXPU()

# Now safe to import diffusers
from diffusers import DiffusionPipeline
import base64
from io import BytesIO

class LocalDiffusionClient:
    def __init__(self):
        self.pipe = None
        self.model_id = "stabilityai/stable-diffusion-xl-base-1.0"
        # Lazy loading: 모델은 처음 요청이 들어올 때 로드합니다. (서버 시작 시간 단축)

    def _load_model(self):
        if self.pipe is None:
            # Device selection logic
            device = "cpu"
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            
            print(f"⏳ Loading Stable Diffusion XL model to {device.upper()} (This may take a while on first run)...")
            try:
                self.pipe = DiffusionPipeline.from_pretrained(
                    self.model_id,
                    torch_dtype=torch.float16,
                    use_safetensors=True,
                    variant="fp16"
                )
                
                self.pipe.to(device)
                
                # Optional: Memory optimization
                # self.pipe.enable_attention_slicing()
                
                print(f"✅ Model loaded successfully on {device.upper()}.")
            except Exception as e:
                print(f"❌ Failed to load model: {e}")
                self.pipe = None

    def generate_image(self, prompt: str) -> str:
        """
        Generate image using local Stable Diffusion XL.
        Returns: Data URI (Base64)
        """
        self._load_model()
        
        if self.pipe is None:
            return None

        try:
            print(f"🎨 Generating image locally with prompt: {prompt[:50]}...")
            
            # Generate
            image = self.pipe(prompt=prompt, num_inference_steps=30).images[0]
            
            # Convert to Base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            print(f"❌ Local Generation Error: {e}")
            return None

local_diffusion_client = LocalDiffusionClient()
