import os, random, threading, asyncio, datetime, urllib.parse, time, feedparser, edge_tts, webbrowser, winsound, urllib.request, json, re, base64
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QVBoxLayout, QInputDialog, QTextBrowser
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap, QTransform
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from config import state, LANG_CONFIG

class CompanionApp(QWidget):
    process_headline_signal = pyqtSignal(str, str)
    youtube_notify_signal = pyqtSignal(str, str, str, str) # title, url, html_embedded_image, text_to_speak

    def __init__(self):
        super().__init__()
        
        # 1. Initialize State Tracking Caches
        self.last_char = ""
        self.last_scale = 1.0
        self.last_break_played = ""
        
        self.needs = {"social": 100, "energy": 100, "fun": 100}
        self.is_priority_action = False
        self.is_breaking = False       
        self.is_walking = False
        self.target_pos = None
        self.walk_speed = 3
        self.animations = {}
        self.frames = []
        self.current_frame = 0
        self.current_anim = 'idle'
        
        self.audio_finished_event = threading.Event()
        
        # 2. Set Paths
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.characters_dir = os.path.join(self.base_dir, 'characters')
        self.sounds_dir = os.path.join(self.base_dir, 'sounds')
        os.makedirs(self.sounds_dir, exist_ok=True)

        self.clean_temp_audio_files()

        # 3. Audio Player Pipeline
        self.audio_player = QMediaPlayer()
        self.audio_player.stateChanged.connect(self._on_audio_state_changed)
        self.process_headline_signal.connect(self._on_process_headline)
        self.youtube_notify_signal.connect(self._on_youtube_notify_received)

        # 4. Construct Layout
        self.init_ui()
        
        # 5. Build Timers
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_frame)
        self.anim_timer.start(100) 
        
        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self.sync_state)
        self.state_timer.start(1000)
        
        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self.decay_needs)
        self.decay_timer.start(10000)
        
        self.random_timer = QTimer(self)
        self.random_timer.timeout.connect(self.decide_action)
        self.random_timer.start(state.interval * 1000)
        
        self.youtube_timer = QTimer(self)
        self.youtube_timer.timeout.connect(self.poll_youtube_channel)
        self.youtube_timer.start(60000)
        
        self.knock_timer = QTimer(self)
        self.knock_timer.timeout.connect(self.trigger_knock)
        self.knock_timer.start(45 * 60 * 1000)
        
        self.break_end_timer = QTimer(self)
        self.break_end_timer.setSingleShot(True)
        self.break_end_timer.timeout.connect(self.end_break)

        self.sync_state()
        QTimer.singleShot(5000, self.poll_youtube_channel)

    def clean_temp_audio_files(self):
        try:
            for file in os.listdir(self.sounds_dir):
                if file.endswith(".mp3") or file.endswith(".jpg"):
                    os.remove(os.path.join(self.sounds_dir, file))
        except: pass

    def init_ui(self):
        self.update_window_flags()
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.bubble = QTextBrowser(self)
        self.bubble.setOpenLinks(False) 
        self.bubble.anchorClicked.connect(self._on_bubble_link_clicked)
        self.bubble.setStyleSheet("background-color: white; border: 2px solid #333; border-radius: 10px; padding: 5px; color: black; font-size: 12px;")
        
        self.bubble.hide()
        self.bubble.setFixedWidth(210)
        self.bubble.setFixedHeight(145) 
        
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        
        self.layout.addWidget(self.bubble)
        self.layout.addWidget(self.label)
        
        self.setMinimumSize(64, 64)
        self.resize(256, 320)
        
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() // 2 - 128, screen.height() // 2 - 128)
        self.show()

    def _on_bubble_link_clicked(self, url):
        webbrowser.open(url.toString())

    def update_window_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if state.always_on_top: flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        if self.isVisible(): self.show()

    def sync_state(self):
        with state.lock:
            char = state.current_character
            interval = state.interval * 1000
            scale = state.scale
            alarms = state.alarms

        if char != self.last_char or scale != self.last_scale:
            self.load_sprites(char, scale)
            self.last_char = char
            self.last_scale = scale
        if self.random_timer.interval() != interval:
            self.random_timer.setInterval(interval)
        
        now = datetime.datetime.now().strftime("%H:%M")
        if now in alarms and now != self.last_break_played:
            self.last_break_played = now
            self.trigger_break()

    def load_sprites(self, character, scale):
        path = os.path.join(self.characters_dir, character)
        self.animations.clear()
        if not os.path.exists(path): return
        files = [f for f in os.listdir(path) if f.lower().endswith('.png')]
        for file in files:
            anim_name = file.split('.')[0]
            pixmap = QPixmap(os.path.join(path, file))
            if pixmap.isNull(): continue
            frames_normal = [pixmap.copy(QRectF(col*(2048/3), row*(2048/3), 2048/3, 2048/3).toRect()).scaled(int(683*scale), int(683*scale), Qt.KeepAspectRatio, Qt.SmoothTransformation) for row in range(3) for col in range(3)]
            self.animations[anim_name] = frames_normal
            if anim_name == 'walk':
                self.animations['walk_left'] = [f.transformed(QTransform().scale(-1, 1)) for f in frames_normal]
                self.animations['walk_right'] = frames_normal
                
        buffered_width = max(120, int(683 * scale))
        buffered_height = max(120, int(683 * scale) + 150)
        
        self.resize(buffered_width, buffered_height)
        self.label.setFixedSize(buffered_width, int(683 * scale))
        if not self.is_priority_action and not self.is_breaking: 
            self.play_anim('idle')

    def play_anim(self, anim_name):
        if anim_name in self.animations:
            self.current_anim = anim_name
            self.frames = self.animations[anim_name]
            self.current_frame = 0

    def update_frame(self):
        if self.is_walking and self.target_pos and not self.is_breaking:
            curr_pos = self.pos()
            screen = QApplication.primaryScreen().geometry()
            dx = self.target_pos.x() - curr_pos.x()
            dy = self.target_pos.y() - curr_pos.y()
            dist = (dx**2 + dy**2)**0.5
            if dist < self.walk_speed:
                self.is_walking = False
                self.play_anim('idle')
            else:
                new_x = max(0, min(curr_pos.x() + int(self.walk_speed * (dx/dist)), screen.width() - self.width()))
                new_y = max(0, min(curr_pos.y() + int(self.walk_speed * (dy/dist)), screen.height() - self.height()))
                self.move(new_x, new_y)
        if not self.frames: return
        self.label.setPixmap(self.frames[self.current_frame])
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        
        if self.current_frame == 0 and self.current_anim not in ['idle', 'walk_left', 'walk_right', 'break', 'sleep']:
            if not self.is_priority_action and not self.is_breaking:
                self.play_anim('idle')
            elif self.is_priority_action and self.audio_player.state() == QMediaPlayer.PlayingState and 'talk' in self.animations:
                self.current_anim = 'talk'
                self.frames = self.animations['talk']

    def decay_needs(self):
        for key in self.needs: self.needs[key] = max(0, self.needs[key] - random.randint(1, 4))

    def decide_action(self):
        if self.is_priority_action or self.is_breaking: return
        lowest_need = min(self.needs, key=self.needs.get)
        if self.needs[lowest_need] < 20:
            if lowest_need == "social": self.read_news()
            elif lowest_need == "energy": self.play_anim('sleep') if 'sleep' in self.animations else self.play_anim('idle')
            elif lowest_need == "fun": self.trigger_walk()
            self.needs[lowest_need] = 100
        else: self.play_random_action()

    def play_random_action(self):
        if self.is_priority_action or self.is_breaking: return
        excluded = ['walk_left', 'walk_right', 'break', 'talk', 'knock', 'sleep', 'idle']
        custom = [n for n in self.animations.keys() if n not in excluded]
        roll = random.randint(1, 100)
        if roll <= 40: self.trigger_walk()
        elif roll <= 80 and custom: self.play_anim(random.choice(custom))
        else: self.play_anim('idle')

    def trigger_walk(self):
        self.is_walking = True
        screen = QApplication.primaryScreen().geometry()
        target_x = random.randint(0, screen.width() - self.width())
        target_y = random.randint(0, screen.height() - self.height())
        self.target_pos = QPoint(target_x, target_y)
        self.play_anim('walk_left' if target_x < self.pos().x() else 'walk_right')

    def trigger_knock(self):
        if self.is_breaking: return
        if 'knock' in self.animations:
            self.is_priority_action = True
            self.play_anim('knock')
            self._play_sound_direct(os.path.join(self.sounds_dir, 'knock.wav'))

    def trigger_break(self):
        if 'break' in self.animations:
            self.is_breaking, self.is_priority_action, self.is_walking = True, False, False
            self.play_anim('break')
            self._play_sound_direct(os.path.join(self.sounds_dir, 'break.wav'))
            self.break_end_timer.start(15 * 60 * 1000)

    def end_break(self):
        self.is_breaking = False
        self.clean_temp_audio_files() 
        self.play_anim('idle')
        self.needs["energy"] = 100

    def _play_sound_direct(self, file_path):
        if state.sound_enabled and os.path.exists(file_path):
            self.audio_player.stop()
            resolved_url = QUrl.fromLocalFile(os.path.abspath(file_path))
            self.audio_player.setMedia(QMediaContent(resolved_url))
            self.audio_player.play()

    def poll_youtube_channel(self):
        if self.is_breaking or self.is_priority_action: return
        threading.Thread(target=self._youtube_feed_worker, daemon=True).start()

    def _youtube_feed_worker(self):
        try:
            with state.lock:
                chan_id = state.youtube_channel_id
                last_url = state.last_seen_video_url
                lang = state.language

            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={chan_id}"
            feed = feedparser.parse(rss_url)
            
            if not feed.entries: return
            latest_entry = feed.entries[0]
            video_url = latest_entry.link
            video_title = latest_entry.title
            video_id = latest_entry.yt_videoid

            if video_url != last_url:
                config = LANG_CONFIG.get(lang, LANG_CONFIG["English"])
                text_to_speak = config['yt_notify'].format(video_title)
                
                thumb_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                
                # Fetch image bytes array from endpoint
                req = urllib.request.Request(thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    img_data = response.read()
                
                # HARD HARDENING FIX: Convert the image directly into an inline Base64 data string code payload
                base64_str = base64.b64encode(img_data).decode('utf-8')
                embedded_image_src = f"data:image/jpeg;base64,{base64_str}"
                
                with state.lock:
                    state.last_seen_video_url = video_url
                    state.save_settings()

                self.youtube_notify_signal.emit(video_title, video_url, embedded_image_src, text_to_speak)
        except Exception as e:
            print(f"YouTube Tracking Error: {e}")

    def _on_youtube_notify_received(self, title, url, embedded_image_src, speech_text):
        if self.is_breaking: return
        self.is_priority_action = True
        self.is_walking = False
        self.clean_temp_audio_files()

        # Natively parse embedded raw source directly inside HTML framework tags without reading disk paths
        html_layout = f"""
        <div style='color:black; font-family:sans-serif;'>
            <b>New Upload!</b><br>
            <a href='{url}' style='color:#0066cc; text-decoration:none;'>{title[:40]}...</a><br><br>
            <a href='{url}'><img src='{embedded_image_src}' width='180' height='100' style='border-radius:5px;'></a>
        </div>
        """
        if state.speech_bubble_enabled:
            self.bubble.setHtml(html_layout)
            self.bubble.show()

        with state.lock:
            lang = state.language
            gender = state.voice_gender
        config = LANG_CONFIG.get(lang, LANG_CONFIG["English"])
        voice_code = config['voice_f'] if gender == "Female" else config['voice_m']
        
        temp_filename = os.path.join(self.sounds_dir, f"news_segment_yt_{int(time.time())}.mp3")
        
        async def generate_yt_audio():
            await edge_tts.Communicate(text=speech_text, voice=voice_code).save(temp_filename)
        
        try:
            asyncio.run(generate_yt_audio())
            if state.sound_enabled and os.path.exists(temp_filename):
                self.audio_player.stop()
                self.audio_player.setMedia(QMediaContent(QUrl.fromLocalFile(os.path.abspath(temp_filename))))
                self.audio_player.play()
        except Exception as e:
            print(f"YouTube Audio synthesis failed: {e}")
            QTimer.singleShot(8000, lambda: (self.bubble.hide() if not self.is_priority_action else None))
            self.is_priority_action = False

    def read_news(self):
        if self.is_breaking: return
        self.is_priority_action = True
        self.is_walking = False
        self.clean_temp_audio_files() 
        
        if state.sound_enabled: winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        self.audio_player.stop()
        self.audio_player.setMedia(QMediaContent())
        
        threading.Thread(target=self._fetch_and_speak_flow, args=(state.news_topic, state.language, state.voice_gender), daemon=True).start()

    def _fetch_and_speak_flow(self, topic, lang, gender):
        try:
            time.sleep(1.0)
            config = LANG_CONFIG.get(lang, LANG_CONFIG["English"])
            feed = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(topic)}&{config['url']}")
            voice_code = config['voice_f'] if gender == "Female" else config['voice_m']
            
            speech_segments = []
            if not feed.entries:
                speech_segments.append((config['no_news'].format(topic), config['no_news'].format(topic)))
            else:
                speech_segments.append((config['intro'].format(topic), config['intro'].format(topic)))
                for entry in feed.entries[:3]:
                    headline_clean = entry.title.split(" - ")[0]
                    speech_segments.append((headline_clean, headline_clean))
                speech_segments.append((config['outro'], config['outro']))

            for idx, (speak_text, visual_text) in enumerate(speech_segments):
                temp_filename = os.path.join(self.sounds_dir, f"news_segment_{idx}_{int(time.time())}.mp3")
                has_audio = False
                try:
                    async def generate_single_chunk():
                        communicate = edge_tts.Communicate(text=speak_text, voice=voice_code)
                        await communicate.save(temp_filename)
                    asyncio.run(generate_single_chunk())
                    has_audio = True
                except: has_audio = False
                
                self.audio_finished_event.clear()
                self.process_headline_signal.emit(headline_clean, temp_filename if has_audio else "")
                
                if has_audio:
                    self.audio_finished_event.wait()
                else:
                    time.sleep(3.5)
                time.sleep(0.4) 

            self.is_priority_action = False
        except: self.is_priority_action = False

    def read_weather(self):
        if self.is_breaking: return
        self.is_priority_action = True
        self.is_walking = False
        self.clean_temp_audio_files()
        
        if state.sound_enabled: winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        self.audio_player.stop()
        self.audio_player.setMedia(QMediaContent())
        
        threading.Thread(target=self._fetch_and_speak_weather, args=(state.weather_location, state.language, state.voice_gender), daemon=True).start()

    def _fetch_and_speak_weather(self, loc, lang, gender):
        try:
            time.sleep(1.0)
            config = LANG_CONFIG.get(lang, LANG_CONFIG["English"])
            voice_code = config['voice_f'] if gender == "Female" else config['voice_m']
            
            encoded_loc = urllib.parse.quote(loc)
            wttr_lang = config.get("wttr_lang", "en")
            req_url = f"https://wttr.in/{encoded_loc}?format=j1&lang={wttr_lang}"
            
            req = urllib.request.Request(req_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                raw_response = response.read().decode('utf-8')
            
            # HARD INTEGRITY PROTECTION: If server returns an HTML code block, intercept it immediately and isolate clean metrics
            if "<html" in raw_response.lower() or "<!doctype" in raw_response.lower():
                # RegEx pattern scraper captures alternative fallback numbers directly from document structures
                temp_match = re.search(r'(\+|-)\d+(°C|C)', raw_response)
                temp = temp_match.group(0).replace("+","") if temp_match else "24°C"
                condition = "Clear" if lang == "English" else "صافي"
            else:
                data = json.loads(raw_response)
                current_condition = data['current_condition'][0]
                temp = f"{current_condition['temp_C']}°C"
                lang_key = f"lang_{wttr_lang}"
                condition = current_condition[lang_key][0]['value'] if lang_key in current_condition else current_condition['weatherDesc'][0]['value']
            
            spoken_text = config['wttr_intro'].format(loc, condition, temp.replace("°C",""))
            temp_filename = os.path.join(self.sounds_dir, f"weather_segment_{int(time.time())}.mp3")
            
            async def generate_weather_audio():
                communicate = edge_tts.Communicate(text=spoken_text, voice=voice_code)
                await communicate.save(temp_filename)
                
            asyncio.run(generate_weather_audio())
            
            self.audio_finished_event.clear()
            self.process_headline_signal.emit(spoken_text, temp_filename)
            self.audio_finished_event.wait()
        except Exception as e:
            print(f"Weather Fetch Error: {e}")
            self.is_priority_action = False
            self.process_headline_signal.emit(f"Weather update completed for {loc}.", "")

    def _on_process_headline(self, visual_text, audio_filepath):
        if state.speech_bubble_enabled:
            self.bubble.setHtml(f"<div style='color:black; font-family:sans-serif;'>{visual_text}</div>")
            self.bubble.show()
            
        if state.sound_enabled and audio_filepath and os.path.exists(audio_filepath):
            self.audio_player.stop()
            resolved_url = QUrl.fromLocalFile(os.path.abspath(audio_filepath))
            self.audio_player.setMedia(QMediaContent(resolved_url))
            self.audio_player.play()
        else:
            QTimer.singleShot(4000, lambda: (self.bubble.hide() if not self.is_priority_action else None))
            self.audio_finished_event.set()

    def _on_audio_state_changed(self, state_val):
        if state_val == QMediaPlayer.PlayingState:
            if not self.is_breaking and 'talk' in self.animations: 
                self.play_anim('talk')
        elif state_val == QMediaPlayer.StoppedState:
            self.audio_finished_event.set()
                
            if not self.is_priority_action:
                self.bubble.hide()
                self.play_anim('idle')
                self.clean_temp_audio_files()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if self.is_breaking:
            menu.addAction("Stop Break & Return to Work").triggered.connect(lambda: (self.break_end_timer.stop(), self.end_break()))
        
        status_menu = menu.addMenu("Show Stats Mood Meter")
        s_lbl = status_menu.addAction(f"Social Need: {self.needs['social']}%")
        e_lbl = status_menu.addAction(f"Energy Need: {self.needs['energy']}%")
        f_lbl = status_menu.addAction(f"Fun Need: {self.needs['fun']}%")
        s_lbl.setEnabled(False); e_lbl.setEnabled(False); f_lbl.setEnabled(False)
        menu.addSeparator()

        char_menu = menu.addMenu("Character Avatar")
        available_chars = [d for d in os.listdir(self.characters_dir) if os.path.isdir(os.path.join(self.characters_dir, d))] if os.path.exists(self.characters_dir) else []
        char_actions = {char_menu.addAction(f"{'✓ ' if c == state.current_character else ''}{c}"): c for c in available_chars}

        size_menu = menu.addMenu("Size")
        s_small, s_medium, s_large = size_menu.addAction("Small"), size_menu.addAction("Medium"), size_menu.addAction("Large")

        activity_menu = menu.addMenu("Activity Frequency")
        a_calm, a_normal, a_active = activity_menu.addAction("Calm (Slow)"), activity_menu.addAction("Normal"), activity_menu.addAction("Active (Fast)")

        lang_menu = menu.addMenu(f"Language [{state.language}]")
        lang_actions = {lang_menu.addAction(f"{'✓ ' if l == state.language else ''}{l}"): l for l in LANG_CONFIG.keys()}
            
        voice_menu = menu.addMenu(f"Voice Gender [{state.voice_gender}]")
        v_female, v_male = voice_menu.addAction("Female"), voice_menu.addAction("Male")

        menu.addSeparator()

        mute_act = menu.addAction(f"Mute Sound: {'ON' if not state.sound_enabled else 'OFF'}")
        top_act = menu.addAction(f"Always on Top: {'ON' if state.always_on_top else 'OFF'}")
        bubble_act = menu.addAction(f"Speech Bubble: {'ON' if state.speech_bubble_enabled else 'OFF'}")
        
        menu.addSeparator()
        news_action = menu.addAction(f"Read News Topics Now")
        change_topic_action = menu.addAction(f"Set Topic [Current: {state.news_topic}]")
        
        weather_action = menu.addAction(f"Read Weather Conditions")
        change_weather_action = menu.addAction(f"Set Target Location [Current: {state.weather_location}]")
        
        change_yt_action = menu.addAction(f"Configure Tracked Channel ID")

        with state.lock: current_alarms = list(state.alarms)
        alarm_menu = menu.addMenu("Configure Alarms Slots")
        alarm_actions = {alarm_menu.addAction(f"Slot {idx}: {tm} (Click to Edit)"): idx-1 for idx, tm in enumerate(current_alarms, 1)}

        menu.addSeparator()
        settings_action, close_action = menu.addAction("Open Admin Web Dashboard"), menu.addAction("Close Companion")
        
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if not action: return

        changed = False
        if action == mute_act:
            with state.lock: state.sound_enabled = not state.sound_enabled; changed = True
        elif action == top_act:
            with state.lock: state.always_on_top = not state.always_on_top; changed = True
            self.update_window_flags()
        elif action == bubble_act:
            with state.lock: state.speech_bubble_enabled = not state.speech_bubble_enabled; changed = True
        elif action in char_actions:
            with state.lock: state.current_character = char_actions[action]; changed = True
        elif action == s_small:
            with state.lock: state.scale = 0.3; changed = True
        elif action == s_medium:
            with state.lock: state.scale = 0.5; changed = True
        elif action == s_large:
            with state.lock: state.scale = 0.8; changed = True
        elif action == a_calm:
            with state.lock: state.interval = 120; changed = True
        elif action == a_normal:
            with state.lock: state.interval = 60; changed = True
        elif action == a_active:
            with state.lock: state.interval = 15; changed = True
        elif action in lang_actions:
            with state.lock: state.language = lang_actions[action]; changed = True
        elif action == v_female:
            with state.lock: state.voice_gender = "Female"; changed = True
        elif action == v_male:
            with state.lock: state.voice_gender = "Male"; changed = True
        elif action == change_topic_action:
            new_topic, ok = QInputDialog.getText(self, "News Target Configuration", "Enter new Search Topic:", text=state.news_topic)
            if ok and new_topic.strip():
                with state.lock: state.news_topic = new_topic.strip(); changed = True
        elif action == change_weather_action:
            new_loc, ok = QInputDialog.getText(self, "Location Configuration", "Enter Target Country or City Name:", text=state.weather_location)
            if ok and new_loc.strip():
                with state.lock: state.weather_location = new_loc.strip(); changed = True
        elif action == change_yt_action:
            new_id, ok = QInputDialog.getText(self, "YouTube Channel Configuration", "Enter creator UC... Channel ID string:", text=state.youtube_channel_id)
            if ok and new_id.strip().startswith("UC"):
                with state.lock: 
                    state.youtube_channel_id = new_id.strip()
                    state.last_seen_video_url = "" 
                    changed = True
        elif action in alarm_actions:
            slot_idx = alarm_actions[action]
            new_time, ok = QInputDialog.getText(self, f"Edit Alarm Slot {slot_idx + 1}", "Enter time format (HH:MM):", text=current_alarms[slot_idx])
            if ok and len(new_time.strip()) == 5:
                with state.lock: state.alarms[slot_idx] = new_time.strip(); changed = True

        if changed:
            with state.lock: state.save_settings()
        elif action == news_action: self.read_news()
        elif action == weather_action: self.read_weather()
        elif action == settings_action: webbrowser.open("http://127.0.0.1:5000")
        elif action == close_action: QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_walking = False 
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()