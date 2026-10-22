import os
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY", "burayageminikey")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

async def ask_gemini(mesaj):
    try:
        response = await asyncio.to_thread(model.generate_content, str(mesaj))
        if response and response.text:
            return response.text.strip()
        return "Cevap alınamadı."
    except Exception as e:
        return f"Hata: {e}"

def geminiai(mesaj):
    try:
        res = model.generate_content(str(mesaj))
        return res.text if res else ""
    except:
        return ""
