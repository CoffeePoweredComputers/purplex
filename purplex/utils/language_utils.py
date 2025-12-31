"""
Language utilities for multilingual support in Purplex.

This module provides constants and utilities for handling multiple languages
across the platform, including UI translations and AI feedback generation.
"""

# Supported languages with metadata
SUPPORTED_LANGUAGES = {
    "en": {
        "name": "English",
        "native": "English",
        "brand": "Purplex",
    },
    "hi": {
        "name": "Hindi",
        "native": "हिन्दी",
        "brand": "पर्प्लेक्स",
    },
    "bn": {
        "name": "Bengali",
        "native": "বাংলা",
        "brand": "পার্পলেক্স",
    },
    "te": {
        "name": "Telugu",
        "native": "తెలుగు",
        "brand": "పర్ప్లెక్స్",
    },
    "pa": {
        "name": "Punjabi",
        "native": "ਪੰਜਾਬੀ",
        "brand": "ਪਰਪਲੈਕਸ",
    },
    "mr": {
        "name": "Marathi",
        "native": "मराठी",
        "brand": "पर्प्लेक्स",
    },
    "kn": {
        "name": "Kannada",
        "native": "ಕನ್ನಡ",
        "brand": "ಪರ್ಪ್ಲೆಕ್ಸ್",
    },
    "ta": {
        "name": "Tamil",
        "native": "தமிழ்",
        "brand": "பர்ப்லெக்ஸ்",
    },
    "ja": {
        "name": "Japanese",
        "native": "日本語",
        "brand": "パープレックス",
    },
    "zh": {
        "name": "Chinese",
        "native": "中文",
        "brand": "紫翎思",
    },
    "pt": {
        "name": "Portuguese",
        "native": "Português",
        "brand": "Purplex",
    },
    "vi": {
        "name": "Vietnamese",
        "native": "Tiếng Việt",
        "brand": "Purplex",
    },
    "th": {
        "name": "Thai",
        "native": "ไทย",
        "brand": "เพอร์เพล็กซ์",
    },
    "es": {
        "name": "Spanish",
        "native": "Español",
        "brand": "Purplex",
    },
    "fr": {
        "name": "French",
        "native": "Français",
        "brand": "Purplex",
    },
    "de": {
        "name": "German",
        "native": "Deutsch",
        "brand": "Purplex",
    },
    "mi": {
        "name": "Māori",
        "native": "Te Reo Māori",
        "brand": "Pāpuraruraru",
    },
}

# Template-based feedback messages for AI comprehension analysis
# These are used by the segmentation service for localized feedback
FEEDBACK_TEMPLATES = {
    "relational": {
        "en": "Excellent! Your {count} segment(s) shows high-level understanding.",
        "hi": "बहुत अच्छा! आपके {count} segment(s) उच्च-स्तरीय समझ दर्शाते हैं।",
        "bn": "চমৎকার! আপনার {count} টি segment উচ্চ-স্তরের বোধগম্যতা দেখায়।",
        "te": "అద్భుతం! మీ {count} విభాగ(లు) ఉన్నత-స్థాయి అవగాహనను చూపిస్తుంది.",
        "pa": "ਬਹੁਤ ਵਧੀਆ! ਤੁਹਾਡੇ {count} ਹਿੱਸੇ ਉੱਚ-ਪੱਧਰੀ ਸਮਝ ਦਰਸਾਉਂਦੇ ਹਨ।",
        "mr": "उत्कृष्ट! तुमचे {count} विभाग उच्च-स्तरीय समज दर्शवतात.",
        "kn": "ಅತ್ಯುತ್ತಮ! ನಿಮ್ಮ {count} ವಿಭಾಗ(ಗಳು) ಉನ್ನತ ಮಟ್ಟದ ತಿಳುವಳಿಕೆಯನ್ನು ತೋರಿಸುತ್ತದೆ.",
        "ta": "அருமை! உங்கள் {count} பிரிவு(கள்) உயர்-நிலை புரிதலை காட்டுகிறது.",
        "ja": "素晴らしい！あなたの{count}つのセグメントは高レベルの理解を示しています。",
        "zh": "太棒了！您的{count}个片段展示了高层次的理解。",
        "pt": "Excelente! Seu(s) {count} segmento(s) mostra(m) compreensão de alto nível.",
        "vi": "Tuyệt vời! {count} phân đoạn của bạn thể hiện sự hiểu biết ở mức cao.",
        "th": "ยอดเยี่ยม! {count} ส่วนของคุณแสดงให้เห็นถึงความเข้าใจระดับสูง",
        "es": "¡Excelente! Tu(s) {count} segmento(s) muestra(n) comprensión de alto nivel.",
        "fr": "Excellent ! Vos {count} segment(s) montre(nt) une compréhension de haut niveau.",
        "de": "Ausgezeichnet! Ihre {count} Segment(e) zeigt/zeigen ein hohes Verständnisniveau.",
        "mi": "Ka rawe! Ko ō wāhanga {count} e whakaatu ana i te māramatanga teitei.",
    },
    "multi_structural": {
        "en": "Your {count} segments are too detailed. Try to describe the overall purpose in {threshold} or fewer segments.",
        "hi": "आपके {count} segments बहुत विस्तृत हैं। {threshold} या कम segments में समग्र उद्देश्य बताने का प्रयास करें।",
        "bn": "আপনার {count} টি segment অত্যন্ত বিস্তারিত। {threshold} বা তার কম segment-এ সামগ্রিক উদ্দেশ্য বর্ণনা করার চেষ্টা করুন।",
        "te": "మీ {count} విభాగాలు చాలా వివరంగా ఉన్నాయి. {threshold} లేదా తక్కువ విభాగాలలో మొత్తం ఉద్దేశ్యాన్ని వివరించడానికి ప్రయత్నించండి.",
        "pa": "ਤੁਹਾਡੇ {count} ਹਿੱਸੇ ਬਹੁਤ ਵਿਸਤ੍ਰਿਤ ਹਨ। {threshold} ਜਾਂ ਘੱਟ ਹਿੱਸਿਆਂ ਵਿੱਚ ਸਮੁੱਚੇ ਉਦੇਸ਼ ਦਾ ਵਰਣਨ ਕਰਨ ਦੀ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
        "mr": "तुमचे {count} विभाग खूप तपशीलवार आहेत. {threshold} किंवा कमी विभागांमध्ये एकूण उद्देश वर्णन करण्याचा प्रयत्न करा.",
        "kn": "ನಿಮ್ಮ {count} ವಿಭಾಗಗಳು ತುಂಬಾ ವಿವರವಾಗಿವೆ. {threshold} ಅಥವಾ ಕಡಿಮೆ ವಿಭಾಗಗಳಲ್ಲಿ ಒಟ್ಟಾರೆ ಉದ್ದೇಶವನ್ನು ವಿವರಿಸಲು ಪ್ರಯತ್ನಿಸಿ.",
        "ta": "உங்கள் {count} பிரிவுகள் மிகவும் விரிவாக உள்ளன. {threshold} அல்லது குறைவான பிரிவுகளில் ஒட்டுமொத்த நோக்கத்தை விவரிக்க முயற்சிக்கவும்.",
        "ja": "あなたの{count}つのセグメントは詳細すぎます。{threshold}つ以下のセグメントで全体の目的を説明してみてください。",
        "zh": "您的{count}个片段过于详细。请尝试用{threshold}个或更少的片段描述整体目的。",
        "pt": "Seus {count} segmentos são muito detalhados. Tente descrever o propósito geral em {threshold} ou menos segmentos.",
        "vi": "{count} phân đoạn của bạn quá chi tiết. Hãy thử mô tả mục đích tổng thể trong {threshold} phân đoạn hoặc ít hơn.",
        "th": "{count} ส่วนของคุณมีรายละเอียดมากเกินไป ลองอธิบายจุดประสงค์โดยรวมใน {threshold} ส่วนหรือน้อยกว่า",
        "es": "Tus {count} segmentos son muy detallados. Intenta describir el propósito general en {threshold} o menos segmentos.",
        "fr": "Vos {count} segments sont trop détaillés. Essayez de décrire l'objectif global en {threshold} segments ou moins.",
        "de": "Ihre {count} Segmente sind zu detailliert. Versuchen Sie, den Gesamtzweck in {threshold} oder weniger Segmenten zu beschreiben.",
        "mi": "He tino taipitopito ō wāhanga {count}. Whakamātauria te whakamārama i te kaupapa whānui i roto i ngā wāhanga {threshold} noa iho.",
    },
}
