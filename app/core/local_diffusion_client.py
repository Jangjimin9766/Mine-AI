import torch
import sys
import base64
import requests
from io import BytesIO
from app.config import settings

# Workaround for diffusers compatibility with PyTorch versions lacking torch.xpu
if not hasattr(torch, 'xpu'):
    class FakeXPU:
        @staticmethod
        def is_available(): return False
        @staticmethod
        def empty_cache(): pass
        @staticmethod
        def device_count(): return 0
    torch.xpu = FakeXPU()

# Lazy import to avoid loading heavy libs when not needed
DiffusionPipeline = None

class LocalDiffusionClient:
    def __init__(self):
        self.pipe = None
        self.model_id = "stabilityai/stable-diffusion-xl-base-1.0"
        self.device = None
        self._load_attempted = False
        
        # Fallback images (Mock Mode)
        self.mock_images = [
            "https://images.unsplash.com/photo-1557683316-973673baf926?w=1200", # Blue Gradient
            "https://images.unsplash.com/photo-1614850523296-d8c1af93d400?w=1200", # Abstract Gold
            "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200", # Minimal Architecture
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200", # Dreamy Beach
            "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1200", # Atmospheric Mountain
        ]

    def _load_model(self) -> bool:
        """Loads model into local GPU if available."""
        if self._load_attempted:
            return self.pipe is not None
        
        self._load_attempted = True
        
        # Check for Local GPU
        if not torch.cuda.is_available() and not (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()):
            print("ℹ️ Local GPU not found. Local generation disabled.")
            return False
            
        try:
            global DiffusionPipeline
            if DiffusionPipeline is None:
                from diffusers import DiffusionPipeline
            
            self.device = "cuda" if torch.cuda.is_available() else "mps"
            print(f"⏳ Loading SDXL to {self.device.upper()}...")
            
            self.pipe = DiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16,
                use_safetensors=True,
                variant="fp16"
            )
            self.pipe.to(self.device)
            print(f"✅ Local GPU model ready on {self.device.upper()}.")
            return True
        except Exception as e:
            print(f"❌ Failed to load local model: {e}")
            return False

    def generate_image(self, prompt: str) -> str:
        """
        Hybrid Generation:
        1. Remote Mode (If REMOTE_IMAGE_SERVER_URL exists)
        2. Local Mode (If local GPU exists)
        3. Mock Mode (Fallback images)
        """
        # --- 1. Remote Mode (e.g. Colab) ---
        if settings.REMOTE_IMAGE_SERVER_URL:
            try:
                print(f"🌐 Requesting image from Remote Server: {settings.REMOTE_IMAGE_SERVER_URL}")
                # Colab server endpoint is expected to take {"prompt": "..."}
                response = requests.post(
                    settings.REMOTE_IMAGE_SERVER_URL, 
                    json={"prompt": prompt},
                    timeout=60
                )
                if response.status_code == 200:
                    data = response.json()
                    image_url = data.get("image_url")
                    if image_url:
                        print("✅ Received image from Remote Server.")
                        return image_url
            except Exception as e:
                print(f"⚠️ Remote request failed: {e}. Falling back...")

        # --- 2. Local Mode ---
        if self._load_model():
            try:
                print(f"🎨 Generating locally (Local GPU)...")
                image = self.pipe(prompt=prompt, num_inference_steps=30).images[0]
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                return f"data:image/png;base64,{img_str}"
            except Exception as e:
                print(f"❌ Local generation failed: {e}")

        # --- 3. Mock Mode (Always works!) ---
        import random
        print("🎭 [Mock Mode] Returning high-quality placeholder image.")
        return random.choice(self.mock_images)

local_diffusion_client = LocalDiffusionClient()
