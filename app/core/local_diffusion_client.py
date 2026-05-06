import torch
import sys
import os
import time

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

DEFAULT_NEGATIVE_PROMPT = (
    "nsfw, nude, naked, violence, blood, gore, sexually explicit, weapons, drugs, horror, "
    "disturbing, offensive, inappropriate, pornographic, erotic, suggestive"
)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class LocalDiffusionClient:
    def __init__(self):
        self.pipe = None
        self.model_id = "stabilityai/stable-diffusion-xl-base-1.0"
        self.device = None
        self._load_attempted = False
        self._load_error = None
        self.last_timing = {}
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

    def generate_image(
        self,
        prompt: str,
        width: int = None,
        height: int = None,
        num_inference_steps: int = None,
        guidance_scale: float = None,
        negative_prompt: str = None,
        output_format: str = None,
        quality: int = None,
    ) -> str:
        """
        Generate image using local Stable Diffusion XL.
        Returns: Data URI (Base64) on success, None on failure
        """
        request_start = time.perf_counter()
        cold_start = not self._load_attempted or self.pipe is None
        load_start = time.perf_counter()
        if not self._load_model():
            self.last_timing = {
                "cold_start": cold_start,
                "model_load_time": round(time.perf_counter() - load_start, 3),
                "image_generation_time": 0,
                "total_time": round(time.perf_counter() - request_start, 3),
                "inference_steps": None,
                "image_width": width,
                "image_height": height,
                "guidance_scale": guidance_scale,
                "negative_prompt_applied": bool(negative_prompt),
                "device": self.device,
                "error": self._load_error,
            }
            print(f"⚠️ SDXL model not available. Status: {self.get_status()}")
            return None

        try:
            print(f"🎨 Generating image locally with prompt: {prompt[:50]}...")
            width = width or _env_int("MOODBOARD_WIDTH", 1024)
            height = height or _env_int("MOODBOARD_HEIGHT", 1024)
            inference_steps = num_inference_steps or _env_int("MOODBOARD_STEPS", _env_int("SDXL_INFERENCE_STEPS", 14))
            guidance_scale = guidance_scale if guidance_scale is not None else _env_float("MOODBOARD_GUIDANCE_SCALE", 6.0)
            negative_prompt = negative_prompt or DEFAULT_NEGATIVE_PROMPT
            output_format = (output_format or os.getenv("MOODBOARD_IMAGE_FORMAT", "JPEG")).upper()
            if output_format == "JPG":
                output_format = "JPEG"
            quality = quality or _env_int("MOODBOARD_IMAGE_QUALITY", 82)
            
            # Generate
            generation_start = time.perf_counter()
            image = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=inference_steps,
                width=width,
                height=height,
                guidance_scale=guidance_scale,
            ).images[0]
            generation_time = time.perf_counter() - generation_start
            
            # Convert to Base64
            buffered = BytesIO()
            if output_format in ("JPEG", "WEBP"):
                image = image.convert("RGB")
            save_kwargs = {}
            if output_format in ("JPEG", "WEBP"):
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            image.save(buffered, format=output_format, **save_kwargs)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            mime_type = "image/jpeg" if output_format == "JPEG" else f"image/{output_format.lower()}"
            self.last_timing = {
                "cold_start": cold_start,
                "model_load_time": round(generation_start - load_start, 3),
                "image_generation_time": round(generation_time, 3),
                "total_time": round(time.perf_counter() - request_start, 3),
                "inference_steps": inference_steps,
                "image_width": width,
                "image_height": height,
                "guidance_scale": guidance_scale,
                "negative_prompt_applied": bool(negative_prompt),
                "output_format": output_format,
                "image_quality": quality,
                "device": self.device,
                "error": None,
            }
            
            print(f"✅ Image generated successfully")
            return f"data:{mime_type};base64,{img_str}"
            
        except Exception as e:
            self.last_timing = {
                "cold_start": cold_start,
                "model_load_time": round(time.perf_counter() - load_start, 3),
                "image_generation_time": 0,
                "total_time": round(time.perf_counter() - request_start, 3),
                "inference_steps": num_inference_steps or _env_int("MOODBOARD_STEPS", _env_int("SDXL_INFERENCE_STEPS", 14)),
                "image_width": width,
                "image_height": height,
                "guidance_scale": guidance_scale,
                "negative_prompt_applied": bool(negative_prompt),
                "device": self.device,
                "error": str(e),
            }
            print(f"❌ Local Generation Error: {e}")
            import traceback
            traceback.print_exc()
            return None


local_diffusion_client = LocalDiffusionClient()
