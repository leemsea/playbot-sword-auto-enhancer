import time
import random
import threading
import sys
from kakao_enhance_bot import KakaoBot

class HeadlessMockBot(KakaoBot):
    def __init__(self, log_callback=None):
        super().__init__(log_callback)
        self.mock_level = 8 # Start at 8
        self.last_command = ""
        self.sell_triggered = False
        self.mock_weapon_name = "혼돈의 쿠키 앤 크림"

    def focus_and_click(self, pos):
        pass

    def send_message(self, text):
        self.last_command = text
        self.log(f"[MOCK] 메시지 전송: {text}")
        if "@플레이봇 판매" in text:
            self.sell_triggered = True

    def get_chat_logs(self):
        if not self.last_command:
            return ""
            
        full_log = "이전 채팅 내역...\n"
        
        if "@플레이봇 강화" in self.last_command:
            self.mock_level += 1
            # Simulate the user reported message
            full_log += f'''[플레이봇] [오전 9:59] @사용자 〖✨강화 성공✨ +{self.mock_level-1} → +{self.mock_level}〗

💬 대장장이: "보여? 이 혼돈 속에서도 균형을 잡아냈어. 흑과 백이 내 손에서 춤추는군!"

💸사용 골드: -5,000G
💰남은 골드: 8,888,076G
⚔️획득 검: [+{self.mock_level}] {self.mock_weapon_name}'''
                
        elif "@플레이봇 판매" in self.last_command:
            full_log += f"판매 완료! +{self.mock_level}강 검을 판매하여 100골드를 획득했습니다."
            self.mock_level = 0
            
        return full_log

def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('cp949', errors='ignore').decode('cp949'))

def test_hidden_weapon_logic():
    print("=== Testing Hidden Weapon Detection & Sell Logic ===")
    
    bot = HeadlessMockBot(log_callback=safe_print)
    bot.goal_level = 15
    bot.enable_sell = True
    bot.normal_sell_level = 11
    bot.hidden_sell_level = 9
    bot.set_coordinates((0,0), (0,0))
    
    # Run in a thread
    t = threading.Thread(target=bot.run_loop)
    t.daemon = True
    t.start()
    
    # Wait for detection
    start_time = time.time()
    while time.time() - start_time < 20: 
        if bot.sell_triggered:
            # Check if it triggered at level 9
            if bot.current_level == 9 and bot.current_weapon_type == "HIDDEN":
                 print("\n✅ SUCCESS: Hidden weapon detected and sold at level 9!")
                 bot.running = False
                 return True
            else:
                 print(f"\n❌ FAIL: Triggered at wrong condition. Level: {bot.current_level}, Type: {bot.current_weapon_type}")
                 bot.running = False
                 return False
                 
        time.sleep(0.5)
        
    bot.running = False
    print("\n❌ TIMEOUT: Sell command NOT detected.")
    return False

if __name__ == "__main__":
    success = test_hidden_weapon_logic()
    sys.exit(0 if success else 1)
