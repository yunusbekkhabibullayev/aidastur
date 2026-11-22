import sys, os
sys.path.append('c:/Users/yunus/Desktop/ai_full/ai')
from backend.app.utils.text_utils import detect_language
samples = ["Dunyoning eng mashur begemoti nobud bo'ldi", "Dunyoning eng mashur begemoti nobud böldi", "O'zbekiston mashhur davlat", "Özbekiston mashhur davlat", "g'alaba yutdi", "ğalaba yutdi", "shahar go'zali", "şahar go'zali", "choy ichamiz", "çoy ichamiz"]
for s in samples:
    print(f"{s} -> {detect_language(s)}")

