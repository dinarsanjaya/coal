import json
import requests
import time
import re
from datetime import datetime

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
        self.stats = {'total_solves': 0, 'total_score': 0, 'failed_attempts': 0}
        
    def request_challenge(self):
        """Request a new COAL mining challenge"""
        url = f"{self.api_url}/api/challenges/request?wallet={self.wallet}"
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                print(f"✓ Challenge received (ID: {data['challengeId']}, Epoch: {data['epoch']})")
                return data
            elif response.status_code == 403 and data.get('error') == 'insufficient_coal':
                print(f"✗ Insufficient COAL: {data.get('message')}")
                print(f"  Minimum: {data.get('minCoal')}, Balance: {data.get('balanceRaw')}")
                return None
            elif response.status_code == 429:
                retry_after = data.get('retryAfter', 1)
                print(f"⏳ Cooldown: wait {retry_after}s")
                time.sleep(retry_after)
                return self.request_challenge()
            else:
                print(f"✗ Error: {data.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"✗ Request failed: {e}")
            return None
    
    def solve_challenge(self, challenge):
        """Use LLM to solve the challenge"""
        doc = challenge['doc']
        questions = challenge['questions']
        
        # Build enhanced prompt for LLM
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
        
        print("🤖 Solving with LLM...")
        
        try:
            # Call LLM API (OpenAI format)
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
                print(f"✗ LLM API error: {response.status_code}")
                return None
            
            result = response.json()
            answer_text = result['choices'][0]['message']['content']
            
            # Parse answers
            answers = self.parse_answers(answer_text)
            
            if len(answers) != 10:
                print(f"✗ Expected 10 answers, got {len(answers)}")
                return None
            
            return answers
            
        except Exception as e:
            print(f"✗ LLM solve failed: {e}")
            return None
    
    def parse_answers(self, text):
        """Parse LLM output into answer array"""
        answers = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Match various formats: Q1: answer, Q1. answer, 1: answer, 1. answer
            match = re.match(r'^Q?\d+[:.)\s]+(.+)$', line, re.IGNORECASE)
            if match:
                answer = match.group(1).strip()
                # Clean up common artifacts
                answer = answer.strip('"\'`')
                answers.append(answer)
            elif line and not re.match(r'^(Q\d+|Question|\d+\.)', line, re.IGNORECASE):
                # Line without question marker - might be continuation
                answer = line.strip('"\'`')
                answers.append(answer)
        
        # Take first 10 answers
        result = answers[:10]
        
        # Debug output
        if len(result) != 10:
            print(f"⚠ Warning: Parsed {len(result)} answers instead of 10")
            print(f"Raw LLM output:\n{text[:500]}")
        
        return result
    
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
                print(f"✓ Submitted! Score: {score}/{total}")
                
                if data.get('txSignature'):
                    print(f"  TX: {data['txSignature']}")
                
                if data.get('failedQuestions'):
                    print(f"  Failed questions: {data['failedQuestions']}")
                
                self.stats['total_solves'] += 1
                self.stats['total_score'] += score
                
                return True
            elif response.status_code == 503 or 'rate limit' in str(data.get('error', '')).lower():
                # RPC rate limit - retry dengan backoff
                if retry_count < 3:
                    wait_time = 10 * (retry_count + 1)
                    print(f"⚠ RPC rate limited. Retrying in {wait_time}s... (attempt {retry_count + 1}/3)")
                    time.sleep(wait_time)
                    return self.submit_answers(challenge_id, answers, retry_count + 1)
                else:
                    print(f"✗ Submit failed after 3 retries: RPC rate limit")
                    return False
            else:
                error_msg = data.get('error', 'Unknown error')
                print(f"✗ Submit failed: {error_msg}")
                if 'message' in data:
                    print(f"  Details: {data['message']}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"✗ Submit timeout")
            return False
        except Exception as e:
            print(f"✗ Submit error: {e}")
            return False
    
    def mine_loop(self, max_attempts=None, auto_restart=True):
        """Main mining loop"""
        print(f"=== COAL Mining Bot ===")
        print(f"Wallet: {self.wallet}")
        print(f"API: {self.api_url}")
        print(f"Model: {self.llm_model}")
        print(f"Auto-restart: {'ON' if auto_restart else 'OFF'}\n")
        
        attempt = 0
        consecutive_failures = 0
        
        try:
            while True:
                attempt += 1
                
                if max_attempts and attempt > max_attempts:
                    print(f"\nReached max attempts ({max_attempts})")
                    break
                
                print(f"\n--- Attempt {attempt} ---")
                
                # Step 1: Request challenge
                challenge = self.request_challenge()
                if not challenge:
                    consecutive_failures += 1
                    if consecutive_failures >= 10 and not auto_restart:
                        print("\n✗ Too many failures. Stopping.")
                        break
                    elif consecutive_failures >= 10:
                        print(f"\n⚠ {consecutive_failures} consecutive failures. Waiting 30s before retry...")
                        time.sleep(30)
                        consecutive_failures = 0  # Reset counter
                    else:
                        time.sleep(5)
                    continue
                
                # Step 2: Solve with LLM
                answers = self.solve_challenge(challenge)
                if not answers or len(answers) != 10:
                    print(f"✗ Invalid answers (got {len(answers) if answers else 0}/10)")
                    consecutive_failures += 1
                    if consecutive_failures >= 10 and not auto_restart:
                        print("\n✗ LLM consistently failing. Stopping.")
                        break
                    elif consecutive_failures >= 10:
                        print(f"\n⚠ LLM issues. Waiting 30s before retry...")
                        time.sleep(30)
                        consecutive_failures = 0
                    continue
                
                # Show answers for debugging
                print("📝 Answers:")
                for i, ans in enumerate(answers, 1):
                    print(f"  Q{i}: {ans}")
                
                # Step 3: Submit
                success = self.submit_answers(challenge['challengeId'], answers)
                
                if success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= 10 and not auto_restart:
                        print("\n✗ Too many failed submissions. Stopping.")
                        break
                    elif consecutive_failures >= 10:
                        print(f"\n⚠ Submit issues. Waiting 30s before retry...")
                        time.sleep(30)
                        consecutive_failures = 0
                
                # Cooldown - tunggu lebih lama untuk avoid rate limit
                print(f"⏳ Waiting {self.cooldown_between_solves}s before next solve...")
                time.sleep(self.cooldown_between_solves)
                
        except KeyboardInterrupt:
            print("\n\n⛏ Mining stopped by user")
        
        # Print stats
        print(f"\n=== Stats ===")
        print(f"Total solves: {self.stats['total_solves']}")
        print(f"Total score: {self.stats['total_score']}")
        if self.stats['total_solves'] > 0:
            avg = self.stats['total_score'] / self.stats['total_solves']
            print(f"Average: {avg:.1f}/10")

if __name__ == "__main__":
    bot = CoalMiningBot()
    bot.mine_loop()
