# 🚀 Google Colab AI Server Setup Guide (Tomorrow's Work)

Because your laptop doesn't have a GPU, we will run the **Mine-AI (Python Server)** on Google Colab and connect it to your local **Mine_server (Spring Boot)**.

## 1. Google Colab Setup
1. Open [Google Colab](https://colab.research.google.com/).
2. Create a new notebook.
3. **Important**: Go to `Runtime` -> `Change runtime type` and select **T4 GPU**.
4. Paste and run the following commands in a cell:

```python
# 1. Clone & Setup
!git clone https://github.com/Jangjimin9766/Mine-AI.git
%cd Mine-AI

# 2. Install dependencies (Wait ~2 mins)
!pip install -r requirements.txt
!pip install pyngrok

# 3. Configure Environment
# Copy your .env content here (GEMINI, GROQ, TAVILY keys)
with open('.env', 'w') as f:
    f.write("GEMINI_API_KEY=your_key\n")
    f.write("GROQ_API_KEY=your_key\n")
    f.write("TAVILY_API_KEY=your_key\n")
    f.write("PYTHON_API_KEY=mine-secret-key-1234\n")

# 4. Start Tunnel (ngrok)
from pyngrok import ngrok
# Sign up at ngrok.com to get your auth token (Free)
!ngrok config add-authtoken YOUR_NGROK_AUTH_TOKEN
public_url = ngrok.connect(8000).public_url
print(f"\n🌍 YOUR PUBLIC API URL: {public_url}")

# 5. Run Server
!uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 2. Local Spring Boot Setup
1. Copy the `public_url` from Colab (e.g., `https://xxxx.ngrok-free.app`).
2. Open `Mine_server`'s `.env` (or `application.yml`).
3. Update `PYTHON_API_URL`:
   ```env
   PYTHON_API_URL=https://xxxx.ngrok-free.app
   ```
4. Restart your Spring Boot server.

## 3. Tomorrow's Verification Checklist
- [ ] **M+MAC Blind Test**: Check if Groq correctly rejects hallucinations in the console logs.
- [ ] **Paragraph Count**: Verify that magazine sections now show **3 paragraphs/images**.
- [ ] **English Search**: Check if Unsplash images match the context using English keywords.
