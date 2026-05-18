import sys
import os
import base64
from dotenv import load_dotenv

# Add app directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.moodboard_maker import generate_moodboard

load_dotenv()

def generate_and_save():
    print("Generating Moodboard for Rilakkuma with M+MAC...")
    result = generate_moodboard(topic="Rilakkuma")
    
    if result.get("success"):
        image_data = result["image_url"] # Base64 Data URI
        if image_data.startswith("data:image"):
            header, encoded = image_data.split(",", 1)
            data = base64.b64decode(encoded)
            
            # Save to artifacts directory
            save_path = r"C:\Users\Lenovo\.gemini\antigravity\brain\851c883f-86e3-4710-8ff3-f132191da4ce\rilakkuma_moodboard.png"
            with open(save_path, "wb") as f:
                f.write(data)
            print(f"Image saved to: {save_path}")
            print(f"Prompt used: {result['description']}")
        else:
            print("Error: Result image_url is not a Data URI.")
    else:
        print(f"Generation failed: {result.get('error')}")

if __name__ == "__main__":
    generate_and_save()
