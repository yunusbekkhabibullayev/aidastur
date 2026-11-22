import re
from typing import Tuple


def normalize_uzbek_text(text: str) -> str:
    """
    O'zbek tilidagi barcha yozuv va alifbo variantlarini standartlashtiradi.
    
    1. Apostrof variantlari (eski va yangi):
       oʻ, gʻ (U+02BB - rasmiy yangi)
       oʼ, gʼ (U+02BC)
       o', g' (U+2018, U+2019)
       o`, g` (U+0060)
       -> Hammasi standart o' va g' ga keltiriladi.
       
    2. Yangi taklif etilgan (turkiy) harflar:
       ö, Ö -> o', O'
       ğ, Ğ -> g', G'
       ş, Ş -> sh, Sh
       ç, Ç -> ch, Ch
    """
    if not text:
        return ""
    
    # 1. Barcha turdagi apostroflarni standart (') ga almashtirish
    apostrophe_variants = '\u02bb\u02bc\u2018\u2019\u0060\u00b4\u2032'
    for ch in apostrophe_variants:
        text = text.replace(ch, "'")
    
    # 2. Yangi turkiy harflarni o'zbek amaldagi lotin harflariga o'tkazish
    char_map = {
        'ö': "o'", 'Ö': "O'",
        'ğ': "g'", 'Ğ': "G'",
        'ş': "sh", 'Ş': "Sh",
        'ç': "ch", 'Ç': "Ch",
    }
    for src, dst in char_map.items():
        text = text.replace(src, dst)
        
    return text


# Kirill <-> Lotin transliteratsiya lug'ati
CYR_TO_LAT = {
    'А': 'A', 'а': 'a', 'Б': 'B', 'б': 'b', 'В': 'V', 'в': 'v',
    'Г': 'G', 'г': 'g', 'Д': 'D', 'д': 'd', 'Е': 'E', 'е': 'e',
    'Ё': 'Yo', 'ё': 'yo', 'Ж': 'J', 'ж': 'j', 'З': 'Z', 'з': 'z',
    'И': 'I', 'и': 'i', 'Й': 'Y', 'й': 'y', 'К': 'K', 'к': 'k',
    'Л': 'L', 'л': 'l', 'М': 'M', 'м': 'm', 'Н': 'N', 'н': 'n',
    'О': 'O', 'о': 'o', 'П': 'P', 'п': 'p', 'Р': 'R', 'р': 'r',
    'С': 'S', 'с': 's', 'Т': 'T', 'т': 't', 'У': 'U', 'у': 'u',
    'Ф': 'F', 'ф': 'f', 'Х': 'X', 'х': 'x', 'Ц': 'Ts', 'ц': 'ts',
    'Ч': 'Ch', 'ч': 'ch', 'Ш': 'Sh', 'ш': 'sh', 'Ъ': "'", 'ъ': "'",
    'Ь': '', 'ь': '', 'Э': 'E', 'э': 'e', 'Ю': 'Yu', 'ю': 'yu',
    'Я': 'Ya', 'я': 'ya', 'Ў': "O'", 'ў': "o'", 'Қ': 'Q', 'қ': 'q',
    'Ғ': "G'", 'ғ': "g'", 'Ҳ': 'H', 'ҳ': 'h'
}

LAT_TO_CYR = {
    "o'": 'ў', "O'": 'Ў', "g'": 'ғ', "G'": 'Ғ',
    "sh": 'ш', "Sh": 'Ш', "SH": 'Ш',
    "ch": 'ч', "Ch": 'Ч', "CH": 'Ч',
    "yo": 'ё', "Yo": 'Ё', "YO": 'Ё',
    "yu": 'ю', "Yu": 'Ю', "YU": 'Ю',
    "ya": 'я', "Ya": 'Я', "YA": 'Я',
    "ye": 'е', "Ye": 'Е', "YE": 'Е',
    'a': 'а', 'A': 'А', 'b': 'б', 'B': 'Б', 'v': 'в', 'V': 'В',
    'g': 'г', 'G': 'Г', 'd': 'д', 'D': 'Д', 'e': 'е', 'E': 'Е',
    'j': 'ж', 'J': 'Ж', 'z': 'з', 'Z': 'З', 'i': 'и', 'I': 'И',
    'y': 'й', 'Y': 'Й', 'k': 'к', 'K': 'К', 'l': 'л', 'L': 'Л',
    'm': 'м', 'M': 'М', 'n': 'н', 'N': 'Н', 'o': 'о', 'O': 'О',
    'p': 'п', 'P': 'П', 'r': 'р', 'R': 'Р', 's': 'с', 'S': 'С',
    't': 'т', 'T': 'Т', 'u': 'у', 'U': 'У', 'f': 'ф', 'F': 'Ф',
    'x': 'х', 'X': 'Х', 'q': 'қ', 'Q': 'Қ', 'h': 'ҳ', 'H': 'Ҳ'
}


def cyrillic_to_latin(text: str) -> str:
    """O'zbekcha kirill yozuvidagi matnni lotin yozuviga o'tkazadi."""
    if not text:
        return ""
    res = []
    i = 0
    while i < len(text):
        # 2 belgili yoki maxsus holatlar (masalan, Е so'z boshida 'Ye')
        ch = text[i]
        if ch in ('Е', 'е'):
            if i == 0 or text[i-1].isspace():
                res.append('Ye' if ch == 'Е' else 'ye')
            else:
                res.append('E' if ch == 'Е' else 'e')
        elif ch in CYR_TO_LAT:
            res.append(CYR_TO_LAT[ch])
        else:
            res.append(ch)
        i += 1
    return "".join(res)


def latin_to_cyrillic(text: str) -> str:
    """O'zbekcha lotin yozuvidagi matnni kirill yozuviga o'tkazadi."""
    if not text:
        return ""
    text = normalize_uzbek_text(text)
    # Avval 2-3 belgili birikmalarni o'giramiz
    for lat, cyr in [("o'", 'ў'), ("O'", 'Ў'), ("g'", 'ғ'), ("G'", 'Ғ'),
                     ("sh", 'ш'), ("Sh", 'Ш'), ("ch", 'ч'), ("Ch", 'Ч'),
                     ("yo", 'ё'), ("Yo", 'Ё'), ("yu", 'ю'), ("Yu", 'Ю'),
                     ("ya", 'я'), ("Ya", 'Я'), ("ye", 'е'), ("Ye", 'Е')]:
        text = text.replace(lat, cyr)
    # Qolgan yakka harflarni o'giramiz
    res = [LAT_TO_CYR.get(ch, ch) for ch in text]
    return "".join(res)


def detect_language(text: str) -> str:
    """
    Kiritilgan matn tilini aniqlaydi (uz, ru, en).
    O'zbek tiliga xos harflar: o', g', sh, ch, ng, q, x
    Kirill harflari bo'lsa: ru yoki uz-cyrl
    """
    text_lower = text.lower()

    # Cyrillic check
    cyrillic_chars = len(re.findall(r'[а-яё]', text_lower))
    latin_chars = len(re.findall(r'[a-z]', text_lower))

    if cyrillic_chars > latin_chars:
        # Check if uzbek cyrillic (ў, қ, ғ, ҳ)
        if re.search(r'[ўқғҳ]', text_lower):
            return "uz"
        return "ru"

    # Lotin yozuvi: o'zbekcha va inglizcha belgilarni sanab solishtiramiz
    words = re.findall(r"[a-z\u02bb\u02bc\u2018\u2019']+", text_lower)
    uz_words = {
        "va", "ham", "uchun", "bilan", "bor", "emas", "deb", "lekin", "haqida", "qaysi", "nima", "qancha",
        "qachon", "kim", "viloyat", "viloyati", "tuman", "shahar", "shahri", "yil", "yilda", "tashkil",
        "etilgan", "qilingan", "bo'lgan", "bo'ladi", "yo'q", "o'zbekiston", "toshkent", "oldin", "keyin",
    }
    uz_suffixes = ("ning", "dagi", "lari", "larni", "ilgan", "tgan", "moqda", "yapti", "yil")
    en_words = {
        "the", "is", "are", "was", "were", "of", "and", "in", "to", "that", "with", "for", "on", "by",
        "which", "who", "what", "when", "where", "how", "does", "did", "has", "have", "from", "this",
    }
    uz_score = sum(1 for w in words if w in uz_words or (len(w) > 5 and w.endswith(uz_suffixes)))
    # Count Uzbek‑specific Latin characters, including both the classic apostrophe forms (o', g')
    # and the newer Turkish‑style letters (ö, ğ, ş, ç). These contribute to the Uzbek language score.
    uz_score += len(re.findall(r"[og][\u02bb\u02bc\u2018\u2019'`]", text_lower))
    uz_score += len(re.findall(r"[öğşç]", text_lower))
    en_score = sum(1 for w in words if w in en_words)

    if en_score > uz_score:
        return "en"
    # Noaniq bo'lsa ilova tili: o'zbekcha
    return "uz"


def clean_text(text: str) -> str:
    """Sanitize and normalize text input."""
    if not text:
        return ""
    # O'zbek apostrof normalizatsiyasi
    text = normalize_uzbek_text(text)
    # Strip dangerous control chars while preserving newlines & punctuation
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def extract_search_keywords(claim_text: str, lang: str = "uz") -> Tuple[str, str]:
    """
    Claim'dan qidiruv so'zlarini generatsiya qiladi:
    1) Umumiy qidiruv query
    2) Fact-check ixtisoslashgan query
    """
    clean_claim = clean_text(claim_text)
    # Remove leading filler phrases if any
    clean_claim = re.sub(r'^(xabar berilishicha|ma\'lum bo\'lishicha|aytishlaricha|deyilishicha|according to|говорят, что)\s*', '', clean_claim, flags=re.I)

    if lang == "uz":
        fc_query = f'{clean_claim} fakt tekshiruv'
    elif lang == "ru":
        fc_query = f'{clean_claim} фактчек'
    else:
        fc_query = f'{clean_claim} fact check'

    return clean_claim, fc_query

