# AI Overview

Savol yoki da'vo kiriting: Vikipediya va internet manbalari asosida, Google AI Overview kabi
manbali javob (kirish gaplari + sarlavhali punktlar + manba belgilari) qaytaradi.

## Ishga tushirish
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r backend\requirements.txt
copy .env.example .env            # va GEMINI_API_KEY ni yozing
python run.py
```
Brauzerda: http://127.0.0.1:8000  |  API hujjatlari: http://127.0.0.1:8000/docs

## Asosiy endpointlar
- `POST /api/overview` - AI Overview uslubidagi javob (hukm va ballsiz)
- `POST /api/check` - eski rejim: TRUE/FALSE/MISLEADING hukmi va ishonchlilik bali
