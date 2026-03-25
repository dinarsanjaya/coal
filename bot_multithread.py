import json
import requests
import time
import re
import threading
from datetime import datetime
from queue import Queue

class CoalMiningBot:
    def __init__(self, config_file='config.json'):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        self.api_url = self.config.get('api_url', 'https://coalmine.fun')
        self.wallet = self.config['wallet']
        self.llm_api_key = self.config['llm_api_key']
        self.llm_api_url = self.config.get('llm_api_url', 'https://api.openai.com/v1')
        self.llm_model = self.config.get('llm_model', 'gpt-4')
        self.cooldown_between_solves = self.config.get('cooldown_seconds', 5)
        
        # Thread-safe stats
        self.stats_lock = threading.Lock()
        self.stats = {'total_solves': 0, 'total_score': 0, 'failed_attempts': 0}
        
    def request_challenge(self):
        """Request a new COAL mining challenge"""
        url = f"{self.api_url}/api/challenges/request?wallet={self.wallet}"
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if response.status_code == 200:
                return data
            elif response.status_code == 403 and data.get('error') == 'insufficient_coal':
                print(f"✗ Insufficient COAL: {data.get('message')}")
                return None
            elif response.status_code == 429:
                retry_after = data.get('retryAfter', 1)
                time.sleep(retry_after)
                return None  # Will retry in main loop
            else:
                return None
                
        except Exception as e:
            return None
    
    def solve_challenge(self, challenge):
        """Use LLM to solve the challenge"""
        doc = challenge['doc']
        questions = challenge['questions']
        
        prompt = f"""You are a precise document analyst. Read this document VERY carefully and answer questions with EXACT accuracy.

DOCUMENT:
{doc}

CRITICAL INSTRUCTIONS:
1. Read the ENTIRE document before answering
2. For INFERENCE questions: Give ONLY the technical term (1-4 words max). Example: "chalcopyrite" NOT "chalcopyrite is a mineral..."
3. For RECALL questions: Copy the EXACT text from document including units. Example: "450 tons" NOT "450" or "450 tonnes"
4. For NUMERIC answers: Use EXACT numbers as stated - do NOT round. "24.19" is different from "24.2"
5. For company names: Use the EXACT name as first mentioned or most commonly used
6. Watch for aliases - companies may have multiple names
7. Ignore hypothetical/speculative statements
8. For "highest/most/largest" questions: Compare ALL mentioned entities carefully

OUTPUT FORMAT:
- Exactly 10 answers
- One per line
- Format: Q1: [answer]
- NO explanations
- NO extra text
- SHORT and EXACT answers only

QUESTIONS:
"""
        for i, q in enumerate(questions, 1):
            prompt += f"Q{i} (type: {q['type']}): {q['question']}\n"
        
        prompt += "\nANSWERS (one per line, Q1: answer format):"
        
        try:
            headers = {
                'Authorization': f'Bearer {self.llm_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.llm_model,
                'messages': [
                    {
                        'role': 'system', 
                        'content': 'You are a precise document analyst. Answer questions with exact accuracy. For inference: give only technical terms. For recall: copy exact text with units. For numbers: use exact precision.'
                    },
                    {
                        'role': 'user', 
                        'content': prompt
                    }
                ],
                'temperature': 0.0,
                'max_tokens': 500
            }
            
            response = requests.post(
                f'{self.llm_api_url}/chat/completions',
                headers=headers,
                json=payload,
                timeout=300
            )
            
            if response.status_code != 200:
                return None
            
            result = response.json()
            answer_text = result['choices'][0]['message']['content']
            answers = self.parse_answers(answer_text)
            
            if len(answers) != 10:
                return None
            
            return answers
            
        except Exception as e:
            return None
    
    def parse_answers(self, text):
        """Parse LLM output into answer array"""
        answers = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            match = re.match(r'^Q?\d+[:.)\s]+(.+)$', line, re.IGNORECASE)
            if match:
                answer = match.group(1).strip()
                answer = answer.strip('"\'`')
                answers.append(answer)
            elif line and not re.match(r'^(Q\d+|Question|\d+\.)', line, re.IGNORECASE):
                answer = line.strip('"\'`')
                answers.append(answer)
        
        return answers[:10]
    
    def submit_answers(self, challenge_id, answers, retry_count=0):
        """Submit answers to COAL API"""
        url = f"{self.api_url}/api/challenges/submit"
        
        payload = {
            'wallet': self.wallet,
            'challengeId': challenge_id,
            'answers': answers
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()
            
            if response.status_code == 200 and data.get('success'):
                score = data['score']
                total = data['total']
                
                with self.stats_lock:
                    self.stats['total_solves'] += 1
                    self.stats['total_score'] += score
                
                return True, score, total, data.get('failedQuestions', [])
            elif response.status_code == 503 or 'rate limit' in str(data.get('error', '')).lower():
                if retry_count < 3:
                    wait_time = 10 * (retry_count + 1)
                    time.sleep(wait_time)
                    return self.submit_answers(challenge_id, answers, retry_count + 1)
                else:
                    return False, 0, 10, []
            else:
                return False, 0, 10, []
                
        except Exception as e:
            return False, 0, 10, []

def worker_thread(bot, thread_id, total_threads, auto_restart=True):
    """Worker thread for mining"""
    print(f"[Thread {thread_id}] Started")
    
    consecutive_failures = 0
    attempt = 0
    
    while True:
        attempt += 1
        
        # Request challenge
        challenge = bot.request_challenge()
        if not challenge:
            consecutive_failures += 1
            
            if consecutive_failures >= 10 and not auto_restart:
                print(f"[Thread {thread_id}] Stopped (too many failures)")
                break
            elif consecutive_failures >= 10:
                print(f"[Thread {thread_id}] ⚠ Too many failures. Waiting 30s...")
                time.sleep(30)
                consecutive_failures = 0
            else:
                time.sleep(2)
            continue
        
        print(f"[Thread {thread_id}] Challenge {challenge['challengeId'][:8]}... (Epoch {challenge['epoch']})")
        
        # Solve
        answers = bot.solve_challenge(challenge)
        if not answers or len(answers) != 10:
            consecutive_failures += 1
            
            if consecutive_failures >= 10 and not auto_restart:
                print(f"[Thread {thread_id}] Stopped (LLM failing)")
                break
            elif consecutive_failures >= 10:
                print(f"[Thread {thread_id}] ⚠ LLM issues. Waiting 30s...")
                time.sleep(30)
                consecutive_failures = 0
            continue
        
        # Submit
        success, score, total, failed = bot.submit_answers(challenge['challengeId'], answers)
        
        if success:
            consecutive_failures = 0
            print(f"[Thread {thread_id}] ✓ Score: {score}/{total}" + 
                  (f" (failed: {failed})" if failed else ""))
        else:
            consecutive_failures += 1
            print(f"[Thread {thread_id}] ✗ Submit failed")
            
            if consecutive_failures >= 10 and not auto_restart:
                print(f"[Thread {thread_id}] Stopped (submit failing)")
                break
            elif consecutive_failures >= 10:
                print(f"[Thread {thread_id}] ⚠ Submit issues. Waiting 30s...")
                time.sleep(30)
                consecutive_failures = 0
        
        # Cooldown - stagger threads to avoid rate limit
        stagger = (thread_id * 2) % total_threads
        time.sleep(bot.cooldown_between_solves + stagger)

def main():
    print("=== COAL Multi-threaded Mining Bot ===\n")
    
    # Load config
    bot = CoalMiningBot()
    
    # Get number of threads
    num_threads = int(input("Number of threads (recommended: 2-4): ") or "2")
    
    # Ask about auto-restart
    auto_restart_input = input("Auto-restart on errors? (yes/no, default: yes): ").strip().lower()
    auto_restart = auto_restart_input != 'no'
    
    print(f"\nStarting {num_threads} mining threads...")
    print(f"Wallet: {bot.wallet}")
    print(f"Model: {bot.llm_model}")
    print(f"Cooldown: {bot.cooldown_between_solves}s")
    print(f"Auto-restart: {'ON' if auto_restart else 'OFF'}\n")
    
    # Start threads
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker_thread, args=(bot, i+1, num_threads, auto_restart))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(1)  # Stagger thread starts
    
    # Monitor
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(10)
            with bot.stats_lock:
                if bot.stats['total_solves'] > 0:
                    avg = bot.stats['total_score'] / bot.stats['total_solves']
                    print(f"\n📊 Stats: {bot.stats['total_solves']} solves, "
                          f"{bot.stats['total_score']} points, avg {avg:.1f}/10")
    except KeyboardInterrupt:
        print("\n\n⛏ Mining stopped by user")
    
    # Wait for threads
    for t in threads:
        t.join(timeout=1)
    
    # Final stats
    print(f"\n=== Final Stats ===")
    print(f"Total solves: {bot.stats['total_solves']}")
    print(f"Total score: {bot.stats['total_score']}")
    if bot.stats['total_solves'] > 0:
        avg = bot.stats['total_score'] / bot.stats['total_solves']
        print(f"Average: {avg:.1f}/10")

if __name__ == "__main__":
    main()
