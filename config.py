import os
import json
import threading

# Centralized Language Configuration Dictionary
LANG_CONFIG = {
    "English": {
        "url": "hl=en-US&gl=US&ceid=US:en",
        "wttr_lang": "en",
        "voice_f": "en-US-AriaNeural",
        "voice_m": "en-US-GuyNeural",
        "no_news": "I couldn't find any recent news about {}.",
        "intro": "Here are the top headlines for {}. ",
        "outro": " That is all for now.",
        "wttr_intro": "The current weather condition for {} is {}, with a temperature of {} degrees celsius.",
        "yt_notify": "New video uploaded on your favorite channel: {}"
    },
    "Arabic": {
        "url": "hl=ar&gl=EG&ceid=EG:ar",
        "wttr_lang": "ar",
        "voice_f": "ar-EG-SalmaNeural",
        "voice_m": "ar-EG-ShakirNeural",
        "no_news": "لم أتمكن من العثور على أخبار حديثة حول {}.",
        "intro": "إليك أهم العناوين حول {}. ",
        "outro": " هذا كل شيء الآن.",
        "wttr_intro": "حالة الطقس الحالية في {} هي {}، ودرجة الحرارة تبلغ {} مئوية.",
        "yt_notify": "فيديو جديد تم رفعه على قناتك المفضلة: {}"
    },
    "Chinese": {
        "url": "hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        "wttr_lang": "zh-cn",
        "voice_f": "zh-CN-XiaoxiaoNeural",
        "voice_m": "zh-CN-YunxiNeural",
        "no_news": "我找不到关于{}的最新新闻。",
        "intro": "以下是关于{}的头条新闻。 ",
        "outro": " 播报完毕。",
        "wttr_intro": "{}目前的天气状况为{}，气温为{}摄氏度。",
        "yt_notify": "您最喜欢的频道有新视频上传：{}"
    },
    "Japanese": {
        "url": "hl=ja&gl=JP&ceid=JP:ja",
        "wttr_lang": "ja",
        "voice_f": "ja-JP-NanamiNeural",
        "voice_m": "ja-JP-KeitaNeural",
        "no_news": "{}に関する最新のニュースは見つかりませんでした。",
        "intro": "{}に関するトップニュースです。 ",
        "outro": " ニュースは以上です。",
        "wttr_intro": "{}の現在のお天気は{}、気温は摂氏{}度です。",
        "yt_notify": "お気に入りのチャンネルに新しい動画がアップロードされました: {}"
    },
    "Korean": {
        "url": "hl=ko&gl=KR&ceid=KR:ko",
        "wttr_lang": "ko",
        "voice_f": "ko-KR-SunHiNeural",
        "voice_m": "ko-KR-InJoonNeural",
        "no_news": "{}에 대한 최근 뉴스를 찾을 수 없습니다.",
        "intro": "{}에 대한 주요 뉴스입니다. ",
        "outro": " 이상입니다.",
        "wttr_intro": "현재 {}의 날씨는 {}이며, 기온은 섭씨 {}도입니다.",
        "yt_notify": "선호하는 채널에 새 동영상이 업로드되었습니다: {}"
    },
    "Spanish": {
        "url": "hl=es&gl=ES&ceid=ES:es",
        "wttr_lang": "es",
        "voice_f": "es-ES-ElviraNeural",
        "voice_m": "es-ES-AlvaroNeural",
        "no_news": "No pude encontrar noticias recientes sobre {}.",
        "intro": "Aquí están los titulares principales de {}. ",
        "outro": " Eso es todo por ahora.",
        "wttr_intro": "El clima actual en {} es {}, con una temperatura de {} grados celsius.",
        "yt_notify": "Nuevo video subido en tu canal favorito: {}"
    },
    "French": {
        "url": "hl=fr&gl=FR&ceid=FR:fr",
        "wttr_lang": "fr",
        "voice_f": "fr-FR-DeniseNeural",
        "voice_m": "fr-FR-HenriNeural",
        "no_news": "Je n'ai pas pu trouver de nouvelles récentes sur {}.",
        "intro": "Voici les gros titres pour {}. ",
        "outro": " C'est tout pour le moment.",
        "wttr_intro": "La météo actuelle pour {} est {}, avec une température de {} degrés celsius.",
        "yt_notify": "Nouvelle vidéo mise en ligne sur votre chaîne préférée: {}"
    }
}

class AppState:
    def __init__(self):
        self.lock = threading.Lock()
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        
        self.current_character = "Bob"
        self.interval = 60         
        self.scale = 0.5           
        self.anim_fps = 10         
        self.news_topic = "Technology"
        self.alarms = ["10:00", "14:00", "18:00"] 
        self.language = "English"
        self.voice_gender = "Female"
        self.speech_bubble_enabled = True
        self.sound_enabled = True
        self.always_on_top = True
        self.weather_location = "New York"
        
        # Tracked YouTube Parameters
        self.youtube_channel_id = "UC1F4CV2YjvxKgNOOFqd_dfQ" # Instantly mapped to Wael Kfoury
        self.last_seen_video_url = ""

        self.load_settings()

    def load_settings(self):
        with self.lock:
            if os.path.exists(self.settings_file):
                try:
                    with open(self.settings_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.current_character = data.get("current_character", self.current_character)
                        self.interval = data.get("interval", self.interval)
                        self.scale = data.get("scale", self.scale)
                        self.news_topic = data.get("news_topic", self.news_topic)
                        self.alarms = data.get("alarms", self.alarms)
                        self.language = data.get("language", self.language)
                        self.voice_gender = data.get("voice_gender", self.voice_gender)
                        self.speech_bubble_enabled = data.get("speech_bubble_enabled", self.speech_bubble_enabled)
                        self.sound_enabled = data.get("sound_enabled", self.sound_enabled)
                        self.always_on_top = data.get("always_on_top", self.always_on_top)
                        self.weather_location = data.get("weather_location", self.weather_location)
                        self.youtube_channel_id = data.get("youtube_channel_id", self.youtube_channel_id)
                        self.last_seen_video_url = data.get("last_seen_video_url", self.last_seen_video_url)
                except: pass

    def save_settings(self):
        try:
            data = {
                "current_character": self.current_character,
                "interval": self.interval,
                "scale": self.scale,
                "news_topic": self.news_topic,
                "alarms": self.alarms,
                "language": self.language,
                "voice_gender": self.voice_gender,
                "speech_bubble_enabled": self.speech_bubble_enabled,
                "sound_enabled": self.sound_enabled,
                "always_on_top": self.always_on_top,
                "weather_location": self.weather_location,
                "youtube_channel_id": self.youtube_channel_id,
                "last_seen_video_url": self.last_seen_video_url
            }
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except: pass

state = AppState()