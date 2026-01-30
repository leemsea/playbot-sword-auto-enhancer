import time
import random
import threading
import tkinter as tk
from kakao_enhance_bot import KakaoBot, BotGUI

class MockKakaoBot(KakaoBot):
    def __init__(self, log_callback=None, stats_callback=None):
        super().__init__(log_callback, stats_callback)
        self.mock_level = 0
        self.mock_gold = 1000
        self.last_command = ""
        self.response_ready_time = 0
        
        # Test scenario: switch between normal and hidden
        self.weapon_pool = [
            ("검", "NORMAL"),
            ("몽둥이", "NORMAL"),
            ("혼돈의 쿠키 앤 크림", "HIDDEN"),
            ("광선검", "HIDDEN"),
            ("젓가락", "HIDDEN")
        ]
        self.current_weapon_name = "검"

    def set_coordinates(self, history_pos, input_pos):
        self.history_pos = history_pos
        self.input_pos = input_pos
        self.log(f"[MOCK] 좌표 설정 완료 (Fake): {history_pos}, {input_pos}")

    def focus_and_click(self, pos):
        # Do nothing in mock
        pass

    def send_message(self, text):
        self.last_command = text
        self.log(f"[MOCK] 메시지 전송: {text}")
        
        # Simulate processing time
        self.response_ready_time = time.time() + 1.0 

    def get_chat_logs(self):
        # Simulate bot response based on last command
        if time.time() < self.response_ready_time:
            return ""

        if not self.last_command:
            return ""
            
        full_log = "이전 채팅 내역...\n"
        
        if "@플레이봇 강화" in self.last_command:
            r = random.random()
            
            # Switch weapon randomly for testing
            if self.mock_level == 0:
                self.current_weapon_name = random.choice(self.weapon_pool)[0]
                
            if r < 0.6: # 60% Success
                self.mock_level += 1
                # Format: ⚔️획득 검: [+9] 혼돈의 쿠키 앤 크림
                # But actually the game format is slightly different depending on version, 
                # but based on user report: ⚔️획득 검: [+9] 혼돈의 쿠키 앤 크림
                # Wait, user report says: ⚔️획득 검: [+9] 혼돈의 쿠키 앤 크림
                # So "검" is the type or category? Or just prefix?
                # User report: ⚔️획득 검: [+9] 혼돈의 쿠키 앤 크림
                # My logic parses after [+9].
                full_log += f"강화 성공! ⚔️획득 검: [+{self.mock_level}] {self.current_weapon_name}"
            elif r < 0.9: # 30% Maintain
                # User report: [+9] 혼돈의 쿠키 앤 크림
                full_log += f"강화 유지! 『[+{self.mock_level}] {self.current_weapon_name}"
            else: # 10% Destroy
                self.mock_level = 0
                full_log += "강화 파괴! 검이 깨졌습니다."
                
        elif "@플레이봇 판매" in self.last_command:
            full_log += f"판매 완료! +{self.mock_level}강 검을 판매하여 100골드를 획득했습니다."
            self.mock_level = 0 # Assume sword is gone/reset
            
        return full_log

class MockBotGUI(BotGUI):
    def __init__(self, root):
        super().__init__(root)
        # Swap the real bot with mock bot
        self.bot = MockKakaoBot(log_callback=self.queue_log, stats_callback=self.update_stats)

def main():
    root = tk.Tk()
    app = MockBotGUI(root)
    root.title("MOCK - 검 키우기 자동 봇")
    root.mainloop()

if __name__ == "__main__":
    main()
