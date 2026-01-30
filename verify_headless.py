import time
import random
import threading
import sys
from kakao_enhance_bot import KakaoBot

class HeadlessMockBot(KakaoBot):
    def __init__(self, log_callback=None):
        super().__init__(log_callback)
        self.mock_level = 9 # Start at 9 to quickly test 10 behavior
        self.last_command = ""
        self.sell_triggered = False

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
            # Always succeed for test to reach 10 quickly
            self.mock_level += 1
            full_log += f"강화 성공! ⚔️획득 검: [+{self.mock_level}]"
                
        elif "@플레이봇 판매" in self.last_command:
            full_log += f"판매 완료! +{self.mock_level}강 검을 판매하여 100골드를 획득했습니다."
            self.mock_level = 0
            
        return full_log

def test_sell_feature():
    print("=== Testing Sell at +10 Feature ===")
    
    bot = HeadlessMockBot(log_callback=print)
    bot.goal_level = 15
    bot.sell_at_10 = True
    bot.set_coordinates((0,0), (0,0))
    
    # Run in a thread, but we will stop it manually
    t = threading.Thread(target=bot.run_loop)
    t.daemon = True
    t.start()
    
    # Wait for a bit
    start_time = time.time()
    while time.time() - start_time < 15: # 15 seconds timeout
        if bot.sell_triggered:
            print("\n✅ Sell command detected!")
            bot.running = False
            return True
        time.sleep(0.5)
        
    bot.running = False
    print("\n❌ Sell command NOT detected within timeout.")
    return False

if __name__ == "__main__":
    success = test_sell_feature()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
