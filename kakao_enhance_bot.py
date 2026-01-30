import time
import re
import sys
import threading
import queue
import tkinter as tk
from tkinter import messagebox, scrolledtext, font
import pyautogui
import pyperclip

# Configuration Constants
DEFAULT_GOAL_LEVEL = 15
DEFAULT_NORMAL_SELL_LEVEL = 11  # 일반 무기 판매 레벨
DEFAULT_HIDDEN_SELL_LEVEL = 9   # 히든 무기 판매 레벨
POLL_INTERVAL = 0.5
TIMEOUT_SECONDS = 10
DELAY_BETWEEN_COMMANDS = 3.0
DROPDOWN_WAIT = 1.0

class KakaoBot:
    def __init__(self, log_callback=None, stats_callback=None):
        self.goal_level = DEFAULT_GOAL_LEVEL
        self.normal_sell_level = DEFAULT_NORMAL_SELL_LEVEL
        self.hidden_sell_level = DEFAULT_HIDDEN_SELL_LEVEL
        self.enable_sell = True
        self.history_pos = None
        self.input_pos = None
        self.running = False
        self.log_callback = log_callback
        self.stats_callback = stats_callback
        self.stop_event = threading.Event()
        self.current_weapon_type = "UNKNOWN"
        self.current_level = 0
        
        # Statistics
        self.sell_count = 0
        self.total_gold_earned = 0

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            try:
                print(message)
            except UnicodeEncodeError:
                # Fallback for Windows consoles that can't handle emojis
                print(message.encode('cp949', errors='ignore').decode('cp949'))

    def set_coordinates(self, history_pos, input_pos):
        self.history_pos = history_pos
        self.input_pos = input_pos
        self.log(f"좌표 설정 완료: 채팅창 {history_pos}, 입력창 {input_pos}")

    def focus_and_click(self, pos):
        pyautogui.moveTo(pos)
        time.sleep(0.1)
        pyautogui.click()

    def send_message(self, text):
        """Types text into the input box and sends it."""
        if not self.input_pos:
            self.log("오류: 좌표가 설정되지 않았습니다.")
            return

        self.focus_and_click(self.input_pos)
        time.sleep(0.2)
        
        # Clear
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        time.sleep(0.1)
        
        # Use simple paste for everything (Slash commands work efficiently)
        # Assuming text is like "/강화" or "/판매"
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2) # Wait for paste
        
        # Press Enter twice to be safe (handles slash command popup if any)
        pyautogui.press('enter')
        time.sleep(0.1)
        pyautogui.press('enter')

    def get_chat_logs(self):
        if not self.history_pos:
            return ""
            
        self.focus_and_click(self.history_pos)
        time.sleep(0.2)
        
        # Method: Click and HOLD, then PageUp while holding
        # 1. Go to end first
        pyautogui.press('end')
        time.sleep(0.1)
        
        # 2. Press and HOLD mouse button (don't release!)
        pyautogui.mouseDown()
        time.sleep(0.3)  # Wait to ensure mouse is held
        
        # 3. While holding, press PageUp to select upwards
        pyautogui.press('pageup')
        time.sleep(0.2)
        
        # 4. Release mouse
        pyautogui.mouseUp()
        time.sleep(0.1)
        
        # 5. Copy
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.2)
        
        try:
            return pyperclip.paste()
        except Exception as e:
            self.log(f"클립보드 오류: {e}")
            return ""

    def parse_last_message(self, full_log):
        keywords = ["강화 성공", "강화 유지", "강화 파괴", "골드가 부족해", "검 판매"] 
        last_idx = -1
        found_keyword = None
        
        for kw in keywords:
            idx = full_log.rfind(kw)
            if idx > last_idx:
                last_idx = idx
                found_keyword = kw
                
        if last_idx == -1:
            return "UNKNOWN", 0, "UNKNOWN", 0, ""

        start_slice = max(0, last_idx - 100)
        end_slice = min(len(full_log), last_idx + 400)
        chunk = full_log[start_slice:end_slice]
        
        status = "UNKNOWN"
        level = 0
        weapon_type = "UNKNOWN"
        gold_earned = 0
        
        # Detect weapon type
        normal_weapons = ["검", "몽둥이", "막대"]
        
        # Look for weapon name patterns
        # Case 1: Success message "⚔️획득 검: [+9] 생명을 잠식하는 검"
        # We need to capture the text AFTER the level tag
        weapon_match = re.search(r'⚔️획득\s*[^:]+:\s*\[\+\d+\]\s*(.+)', chunk)
        if weapon_match:
            weapon_name = weapon_match.group(1).strip()
            # Check if weapon name ENDS WITH any normal weapon
            if any(weapon_name.endswith(nw) for nw in normal_weapons):
                weapon_type = "NORMAL"
            else:
                weapon_type = "HIDDEN"
        else:
            # Case 2: Maintain message "『[+9] 생명을 잠식하는 검"
            # Or standard format: "『[+9] 검"
            # Let's try to capture text after [+N]
            weapon_match = re.search(r'『\[\+\d+\]\s*(.+)', chunk)
            if weapon_match:
                weapon_name = weapon_match.group(1).strip()
                # Remove trailing brackets if any (sometimes happens with copy)
                weapon_name = weapon_name.split('\n')[0].strip() 
                
                # Check if weapon name ENDS WITH any normal weapon
                if any(weapon_name.endswith(nw) for nw in normal_weapons):
                    weapon_type = "NORMAL"
                else:
                    weapon_type = "HIDDEN"
        
        if found_keyword == "강화 성공":
            status = "SUCCESS"
            match = re.search(r'⚔️획득\s+[^:：]+[：:]\s*\[\+(\d+)\]', chunk)
            if not match:
                 match = re.search(r'→\s*\+(\d+)', chunk)
            if match:
                level = int(match.group(1))
                
        elif found_keyword == "강화 유지":
            status = "MAINTAIN"
            # Pattern: "『[+2] 검』의 레벨이 유지되었습니다" or "『[+2] 생명을 다루는 검』의 레벨이 유지되었습니다"
            maintain_match = re.search(r'『\[(\+\d+)\]\s*(.+?)』', chunk)
            if maintain_match:
                level_str = maintain_match.group(1)  # "+2"
                weapon_name = maintain_match.group(2).strip()  # "검" or "생명을 다루는 검"
                level = int(level_str.replace('+', ''))
                
                # Determine weapon type from name
                normal_weapons = ["검", "몽둥이", "막대"]
                if any(weapon_name.endswith(nw) for nw in normal_weapons):
                    weapon_type = "NORMAL"
                else:
                    weapon_type = "HIDDEN"
            else:
                # Fallback: try old pattern
                match = re.search(r'『[^\[]+\[(\+\d+)\]', chunk)
                if match:
                    level_str = match.group(1)
                    level = int(level_str.replace('+', ''))
            
        elif found_keyword == "강화 파괴":
            status = "DESTROY"
            level = 0
            
        elif found_keyword == "골드가 부족해":
            status = "NO_GOLD"
            level = 0
            
        elif found_keyword == "검 판매":
            status = "SELL_COMPLETE"
            # Pattern: "💶획득 골드: +189,726G"
            gold_match = re.search(r'💶획득 골드:\s*\+([\d,]+)G', chunk)
            if gold_match:
                gold_str = gold_match.group(1).replace(',', '')  # Remove commas
                gold_earned = int(gold_str)
            level = 0  # After selling, we have no weapon

        return status, level, weapon_type, gold_earned, chunk

    def check_initial_status(self):
        """Check current status using /프로필 command before starting the loop."""
        self.log("현재 상태 확인 중...")
        self.log(">> /프로필 명령 전송...")
        
        # Send profile command
        self.send_message("/프로필")
        time.sleep(3.0)  # Wait for response
        
        # Get chat logs
        logs = self.get_chat_logs()
        self.log(f"[DEBUG check_initial_status] 복사된 로그 길이: {len(logs) if logs else 0}자")
        
        if not logs:
            self.log("   ⚠️ 채팅 내역을 읽을 수 없습니다. 0강부터 시작합니다.")
            return
        
        # Parse profile response: "● 보유 검: [+7] 생명의 정수를 빚어내는 검"
        profile_match = re.search(r'● 보유 검:\s*\[(\+\d+)\]\s*(.+)', logs)
        
        if profile_match:
            level_str = profile_match.group(1)  # "+7"
            weapon_name = profile_match.group(2).strip()  # "생명의 정수를 빚어내는 검"
            # Remove any trailing newlines or description text
            weapon_name = weapon_name.split('\n')[0].strip()
            
            level = int(level_str.replace('+', ''))
            
            # Determine weapon type
            normal_weapons = ["검", "몽둥이", "막대"]
            if any(weapon_name.endswith(nw) for nw in normal_weapons):
                weapon_type = "NORMAL"
            else:
                weapon_type = "HIDDEN"
            
            self.current_level = level
            self.current_weapon_type = weapon_type
            
            weapon_text = "일반" if weapon_type == "NORMAL" else "히든"
            self.log(f"   ✅ 현재 상태: {weapon_text} 무기 +{level} ({weapon_name})")
            self.log(f"[DEBUG] weapon_name='{weapon_name}', ends_with_check={[weapon_name.endswith(nw) for nw in normal_weapons]}")
        else:
            self.log("   ℹ️ 현재 강화된 무기가 없습니다. 0강부터 시작합니다.")
            self.log(f"[DEBUG] 프로필 파싱 실패. 로그 일부: {logs[:200]}")

    def run_loop(self):
        self.running = True
        self.stop_event.clear()
        
        # Check initial status first
        self.check_initial_status()
        
        last_seen_chunk = ""
        consecutive_errors = 0
        
        sell_info = f"일반 {self.normal_sell_level}강 / 히든 {self.hidden_sell_level}강" if self.enable_sell else "OFF"
        self.log(f"봇 시작: 목표 +{self.goal_level}, 판매 설정 [{sell_info}]")
        
        while self.running and not self.stop_event.is_set():
            try:
                # 0. Pre-Check Phase: Should I sell or stop already?
                # This prevents "Enhancing a +11 item" if we started with it.
                self.log(f"[DEBUG Pre-Check] enable_sell={self.enable_sell}, current_level={self.current_level}, current_weapon_type={self.current_weapon_type}, normal_sell={self.normal_sell_level}, hidden_sell={self.hidden_sell_level}")
                
                if self.enable_sell:
                    should_sell = False
                    if self.current_weapon_type == "NORMAL" and self.current_level >= self.normal_sell_level:
                        should_sell = True
                        self.log(f"   [상태 체크] 일반 무기 {self.current_level}강 (목표 {self.normal_sell_level}강) -> 판매 대상!")
                    elif self.current_weapon_type == "HIDDEN" and self.current_level >= self.hidden_sell_level:
                        should_sell = True
                        self.log(f"   [상태 체크] 히든 무기 {self.current_level}강 (목표 {self.hidden_sell_level}강) -> 판매 대상!")
                    else:
                        self.log(f"[DEBUG] 판매 조건 미충족 - Level: {self.current_level}, Type: {self.current_weapon_type}")
                    
                    if should_sell:
                        self.log(">> 판매 조건 충족! 판매를 시도합니다.")
                        # Call execution block for selling
                        # To avoid duplication, we will fall through to logic or duplicate the sell block here.
                        # Since we want to act immediately, we will execute sell here.
                        time.sleep(1.0)
                        self.send_message("/판매")
                        self.log("   (판매 명령 전송됨)")
                        
                        time.sleep(3.0)
                        sell_logs = self.get_chat_logs()
                        sell_status, _, _, sell_gold, _ = self.parse_last_message(sell_logs)
                        
                        if sell_status == "SELL_COMPLETE" and sell_gold > 0:
                            self.sell_count += 1
                            self.total_gold_earned += sell_gold
                            self.log(f"   💵 판매 완료! {sell_gold}골드 획득 (총 {self.sell_count}회 판매, {self.total_gold_earned}골드 획득)")
                            if self.stats_callback:
                                self.stats_callback(self.sell_count, self.total_gold_earned)
                        
                        self.current_level = 0
                        self.current_weapon_type = "UNKNOWN"
                        time.sleep(DELAY_BETWEEN_COMMANDS)
                        continue

                # 1. Action Phase
                self.log(f">> 강화 명령 전송... (현재: +{self.current_level} {self.current_weapon_type})")
                self.send_message("/강화")
                
                # 2. Wait Phase
                self.log("   (응답 대기 중...)")
                time.sleep(5.0)
                
                start_wait = time.time()
                got_new_reply = False
                
                current_level = 0
                current_status = "UNKNOWN"
                current_weapon_type = "UNKNOWN"
                current_gold_earned = 0

                # 3. Poll Phase
                while time.time() - start_wait < TIMEOUT_SECONDS:
                    if self.stop_event.is_set(): break
                    time.sleep(POLL_INTERVAL)
                    
                    logs = self.get_chat_logs()
                    if not logs: continue
                    
                    status, level, weapon_type, gold_earned, chunk = self.parse_last_message(logs)
                    
                    if chunk != last_seen_chunk and status != "UNKNOWN":
                        last_seen_chunk = chunk
                        got_new_reply = True
                        current_level = level
                        current_status = status
                        current_weapon_type = weapon_type
                        current_gold_earned = gold_earned
                        
                        weapon_text = "일반" if weapon_type == "NORMAL" else ("히든" if weapon_type == "HIDDEN" else "?")
                        self.log(f"   [응답] 상태: {status} | 레벨: {level} | 무기: {weapon_text}")
                        break
                
                if self.stop_event.is_set(): break

                # 4. Logic Phase
                if got_new_reply:
                    consecutive_errors = 0
                    
                    if current_status == "SUCCESS":
                        self.current_level = current_level
                        self.current_weapon_type = current_weapon_type
                        
                        self.log(f"   ✨ 성공! +{current_level}")
                        
                        # Check Goal
                        if current_level >= self.goal_level:
                            self.log(f"🎉 목표 레벨({self.goal_level}) 달성! 종료합니다.")
                            self.running = False
                            break

                        # Check Sell Condition (Post-Enhance Step Removed - moved to Pre-Check)
                        # Just update state and loop; Pre-Check will handle selling on next iteration
                        pass 

                    elif current_status == "MAINTAIN":
                        # CRITICAL: Update state even on MAINTAIN!
                        self.current_level = current_level
                        self.current_weapon_type = current_weapon_type
                        self.log(f"   💦 유지. 재시도... (현재 레벨: +{current_level})")
                        
                    elif current_status == "DESTROY":
                        self.log("   💥 파괴. 다시 시작...")
                        self.current_level = 0
                        self.current_weapon_type = "UNKNOWN"
                        
                    elif current_status == "NO_GOLD":
                        self.log("   💰 골드 부족. 종료합니다.")
                        self.running = False
                        break
                        
                else:
                    self.log("   ⚠️ 응답 없음. 재시도...")
                    consecutive_errors += 1
                    if consecutive_errors >= 5:
                        self.log("   ❌ 연속 타임아웃. 종료.")
                        self.running = False
                        break
                
                time.sleep(DELAY_BETWEEN_COMMANDS)
                
            except Exception as e:
                self.log(f"❌ 오류 발생: {e}")
                self.running = False
                break
        
        self.log("봇이 정지되었습니다.")

class CalibrationWindow:
    def __init__(self, master, callback):
        self.master = master
        self.callback = callback
        self.top = tk.Toplevel(master)
        self.top.title("좌표 보정")
        self.top.geometry("350x250")
        
        # Make the window stay on top
        self.top.attributes('-topmost', True)
        
        self.step = 1
        self.history_pos = None
        
        self.label = tk.Label(self.top, text="[단계 1]\n\n채팅 내역(대화창 오른쪽 아래)\n마우스를 올리고\nEnter 키를 누르세요.", font=("Arial", 12))
        self.label.pack(expand=True, fill="both", padx=20, pady=20)
        
        self.top.bind('<Return>', self.on_enter)
        self.top.focus_force()

    def on_enter(self, event):
        pos = pyautogui.position()
        if self.step == 1:
            self.history_pos = pos
            self.step = 2
            self.label.config(text=f"채팅창 위치 저장됨:\n{pos}\n\n[단계 2]\n입력창(글 쓰는 곳) 위에\n마우스를 올리고\nEnter 키를 누르세요.")
        elif self.step == 2:
            input_pos = pos
            self.callback(self.history_pos, input_pos)
            self.top.destroy()

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("검 키우기 자동 봇")
        self.root.geometry("600x850")
        
        # Thread-safe logging and stats
        self.log_queue = queue.Queue()
        self.bot = KakaoBot(log_callback=self.queue_log, stats_callback=self.update_stats)
        self.bot_thread = None
        
        # UI Setup
        self.create_widgets()
        
        # Start queue poller
        self.process_log_queue()

    def create_widgets(self):
        # Fonts
        font_title = font.Font(family="Arial", size=14, weight="bold")
        font_normal = font.Font(family="Arial", size=10)
        
        # Main Container
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        # Header
        tk.Label(main_frame, text="검 키우기 자동 봇", font=font_title).pack(pady=(0, 15))
        # tk.Label(main_frame, text="초등학생도 쉽게 쓰는 자동 강화!", font=font_normal, fg="gray").pack(pady=(0, 15))

        # 1. Settings Frame
        frame_settings = tk.LabelFrame(main_frame, text="설정", font=("Arial", 10, "bold"), padx=10, pady=10)
        frame_settings.pack(fill="x", pady=5)
        
        # Goal Level
        frame_goal = tk.Frame(frame_settings)
        frame_goal.pack(fill="x", pady=5)
        tk.Label(frame_goal, text="목표 레벨:", font=font_normal).pack(side="left")
        self.spin_goal = tk.Spinbox(frame_goal, from_=1, to=30, width=5, font=font_normal)
        self.spin_goal.delete(0, "end")
        self.spin_goal.insert(0, DEFAULT_GOAL_LEVEL)
        self.spin_goal.pack(side="left", padx=5)
        
        # Sell Settings
        tk.Label(frame_settings, text="━━━ 자동 판매 설정 ━━━", font=("Arial", 9)).pack(pady=(10, 5))
        
        self.var_enable_sell = tk.BooleanVar(value=True)
        tk.Checkbutton(frame_settings, text="자동 판매 사용", variable=self.var_enable_sell, 
                      font=font_normal, command=self.toggle_sell).pack(anchor="w", pady=2)
        
        # Normal Weapon Sell Level
        frame_normal = tk.Frame(frame_settings)
        frame_normal.pack(fill="x", pady=5)
        tk.Label(frame_normal, text="일반 무기 (검/몽둥이/막대):", font=("Arial", 9)).pack(anchor="w")
        
        frame_normal_slider = tk.Frame(frame_normal)
        frame_normal_slider.pack(fill="x", pady=2)
        self.scale_normal = tk.Scale(frame_normal_slider, from_=0, to=20, orient="horizontal", 
                                     command=self.update_normal_label)
        self.scale_normal.set(DEFAULT_NORMAL_SELL_LEVEL)
        self.scale_normal.pack(side="left", expand=True, fill="x")
        self.label_normal = tk.Label(frame_normal_slider, text=f"{DEFAULT_NORMAL_SELL_LEVEL}강", 
                                     width=5, font=("Arial", 10, "bold"))
        self.label_normal.pack(side="right", padx=5)
        
        # Hidden Weapon Sell Level
        frame_hidden = tk.Frame(frame_settings)
        frame_hidden.pack(fill="x", pady=5)
        tk.Label(frame_hidden, text="히든 무기 (젓가락/우산/광선검 등):", font=("Arial", 9)).pack(anchor="w")
        
        frame_hidden_slider = tk.Frame(frame_hidden)
        frame_hidden_slider.pack(fill="x", pady=2)
        self.scale_hidden = tk.Scale(frame_hidden_slider, from_=0, to=20, orient="horizontal",
                                     command=self.update_hidden_label)
        self.scale_hidden.set(DEFAULT_HIDDEN_SELL_LEVEL)
        self.scale_hidden.pack(side="left", expand=True, fill="x")
        self.label_hidden = tk.Label(frame_hidden_slider, text=f"{DEFAULT_HIDDEN_SELL_LEVEL}강", 
                                     width=5, font=("Arial", 10, "bold"))
        self.label_hidden.pack(side="right", padx=5)
        
        # 2. Control Frame
        frame_controls = tk.Frame(main_frame, pady=10)
        frame_controls.pack(fill="x")
        
        self.btn_calib = tk.Button(frame_controls, text="1. 좌표 설정 (필수)", command=self.start_calibration, 
                                   bg="#A0D8EF", fg="black", font=("Arial", 11, "bold"), height=2)
        self.btn_calib.pack(fill="x", pady=5)

        self.btn_test_copy = tk.Button(frame_controls, text="테스트: 복사 확인", command=self.test_copy,
                                      bg="#E0E0E0", fg="black", font=("Arial", 9))
        self.btn_test_copy.pack(fill="x", pady=(0, 5))
        
        frame_btns = tk.Frame(frame_controls)
        frame_btns.pack(fill="x", pady=5)
        
        self.btn_start = tk.Button(frame_btns, text="▶ 시작", command=self.start_bot, 
                                   bg="#90EE90", fg="black", font=("Arial", 11, "bold"), height=2, state="disabled")
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.btn_stop = tk.Button(frame_btns, text="⏹ 중지", command=self.stop_bot, 
                                  bg="#FFB6C1", fg="black", font=("Arial", 11, "bold"), height=2, state="disabled")
        self.btn_stop.pack(side="right", expand=True, fill="x", padx=(5, 0))
        
        # 3. Statistics Frame
        frame_stats = tk.LabelFrame(main_frame, text="📊 판매 통계", font=("Arial", 10, "bold"), padx=10, pady=8)
        frame_stats.pack(fill="x", pady=(10, 5))
        
        stats_content = tk.Frame(frame_stats)
        stats_content.pack(fill="x")
        
        # Sell count
        frame_sell_count = tk.Frame(stats_content)
        frame_sell_count.pack(side="left", expand=True, fill="x", padx=5)
        tk.Label(frame_sell_count, text="판매 횟수:", font=("Arial", 9)).pack(side="left")
        self.label_sell_count = tk.Label(frame_sell_count, text="0회", font=("Arial", 11, "bold"), fg="#FF6B6B")
        self.label_sell_count.pack(side="left", padx=5)
        
        # Total gold
        frame_gold = tk.Frame(stats_content)
        frame_gold.pack(side="right", expand=True, fill="x", padx=5)
        tk.Label(frame_gold, text="총 획득 골드:", font=("Arial", 9)).pack(side="left")
        self.label_total_gold = tk.Label(frame_gold, text="0G", font=("Arial", 11, "bold"), fg="#FFD700")
        self.label_total_gold.pack(side="left", padx=5)
        
        # 4. Log Frame
        frame_log = tk.LabelFrame(main_frame, text="실행 로그", font=("Arial", 10))
        frame_log.pack(expand=True, fill="both", pady=(10, 0))
        
        self.text_log = scrolledtext.ScrolledText(frame_log, state="disabled", height=18, font=("Consolas", 9))
        self.text_log.pack(expand=True, fill="both", padx=5, pady=5)
        
        # Initial Log
        self.queue_log("프로그램이 실행되었습니다.")
        self.queue_log("먼저 '좌표 설정' 버튼을 눌러주세요.")

    def update_normal_label(self, value):
        self.label_normal.config(text=f"{value}강")
    
    def update_hidden_label(self, value):
        self.label_hidden.config(text=f"{value}강")
    
    def toggle_sell(self):
        enabled = self.var_enable_sell.get()
        state = "normal" if enabled else "disabled"
        self.scale_normal.config(state=state)
        self.scale_hidden.config(state=state)

    def queue_log(self, msg):
        self.log_queue.put(msg)

    def update_stats(self, sell_count, total_gold):
        """Thread-safe statistics update."""
        self.root.after(0, lambda: self.label_sell_count.config(text=f"{sell_count}회"))
        self.root.after(0, lambda: self.label_total_gold.config(text=f"{total_gold:,}G"))

    def process_log_queue(self):
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.text_log.config(state="normal")
                self.text_log.insert("end", f"{msg}\n")
                self.text_log.see("end")
                self.text_log.config(state="disabled")
            except queue.Empty:
                break
        
        # Check thread status
        if self.bot_thread and not self.bot_thread.is_alive() and self.btn_stop['state'] == 'normal':
             self.btn_start.config(state="normal")
             self.btn_stop.config(state="disabled")
             self.btn_calib.config(state="normal")

        self.root.after(100, self.process_log_queue)

    def start_calibration(self):
        CalibrationWindow(self.root, self.on_calibration_complete)

    def on_calibration_complete(self, history_pos, input_pos):
        self.bot.set_coordinates(history_pos, input_pos)
        self.btn_start.config(state="normal")
        self.queue_log("✅ 좌표 설정 완료! 이제 시작할 수 있습니다.")

    def start_bot(self):
        if self.bot.running:
            return
            
        try:
            self.bot.goal_level = int(self.spin_goal.get())
            self.bot.enable_sell = self.var_enable_sell.get()
            self.bot.normal_sell_level = int(self.scale_normal.get())
            self.bot.hidden_sell_level = int(self.scale_hidden.get())
        except ValueError:
            messagebox.showerror("오류", "목표 레벨은 숫자여야 합니다.")
            return

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_calib.config(state="disabled")
        self.spin_goal.config(state="disabled")
        self.var_enable_sell.set(self.var_enable_sell.get())  # Lock checkbox
        self.scale_normal.config(state="disabled")
        self.scale_hidden.config(state="disabled")
        
        self.bot_thread = threading.Thread(target=self.bot.run_loop)
        self.bot_thread.daemon = True 
        self.bot_thread.start()

    def stop_bot(self):
        if self.bot.running:
            self.bot.stop_event.set()
            self.queue_log("중지 요청 중... (현재 작업 완료 후 멈춥니다)")
            self.btn_stop.config(state="disabled")
            
            # Re-enable controls
            self.btn_start.config(state="normal")  # Re-enable start button
            self.btn_calib.config(state="normal")
            self.spin_goal.config(state="normal")
            self.scale_normal.config(state="normal" if self.var_enable_sell.get() else "disabled")
            self.scale_hidden.config(state="normal" if self.var_enable_sell.get() else "disabled")
            self.btn_test_copy.config(state="normal")

    def test_copy(self):
        """Test copy logic on demand."""
        if not self.bot.history_pos:
            messagebox.showwarning("주의", "좌표 설정이 필요합니다.")
            return

        self.queue_log("[테스트] 채팅 로그 복사 시도 중...")
        logs = self.bot.get_chat_logs()
        if logs:
            self.queue_log(f"[테스트 성공] {len(logs)} 글자 복사됨.")
            # Show preview (Last 500 chars to be safe, but focus on content)
            preview = logs[-500:] if len(logs) > 500 else logs
            messagebox.showinfo("복사 테스트 결과", f"성공적으로 복사했습니다! (총 {len(logs)}자)\n\n--- [마지막 내용을 확인하세요] ---\n{preview}")
        else:
            self.queue_log("[테스트 실패] 복사된 내용이 없습니다.")
            messagebox.showerror("오류", "복사된 내용이 없습니다.\n좌표를 다시 확인해주세요.")

def main():
    root = tk.Tk()
    app = BotGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
