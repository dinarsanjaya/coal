import json
import requests
import time
import re
import os
from datetime import datetime, timedelta
from pathlib import Path

class CoalMiningBotOptimized:
    def __init__(self, config_file='config.json'):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        self.api_url = self.config.get('api_url', 'https://coalmine.fun')
        self.wallet = self.config['wallet']
        self.llm_api_key = self.config['llm_api_key']
        self.llm_api_url = self.config.get('llm_api_url', 'https://api.openai.com/v1')
        self.llm_model = self.config.get('llm_model', 'gpt-4')
        self.cooldown_between_solves = self.config.get('cooldown_seconds', 5)
        self.stats_file = 'mining_stats.json'
        self.stats = self.load_stats()
        self.session = requests.Session()  # Reuse connections
        self.last_rank_check = 0
        self.cached_rank = None
        self.cached_total = None
        
    def load_stats(self):
        """Load stats from file"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'total_solves': 0,
            'total_score': 0,
            'perfect_scores': 0,
            'failed_attempts': 0,
            'history': [],
            'start_time': datetime.now().isoformat()
        }
    
    def save_stats(self):
        """Save stats to file"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            pass
    
    def request_challenge(self, retry_count=0):
        """Request a new COAL mining challenge with retry logic"""
        url = f"{self.api_url}/api/challenges/request?wallet={self.wallet}"
        
        try:
            response = self.session.get(url, timeout=15)
            data = response.json()
            
            if response.status_code == 200:
                return data
            elif response.status_code == 429:
                if data.get('error') == 'active_challenge' and 'challengeId' in data:
                    # Recover active challenge
                    return data
                retry_after = data.get('retryAfter', 1)
                time.sleep(retry_after)
                return None
            elif response.status_code == 403:
                # Insufficient COAL - fatal error
                return None
            else:
                if retry_count < 3:
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    return self.request_challenge(retry_count + 1)
                return None
                
        except Exception as e:
            if retry_count < 3:
                time.sleep(2 ** retry_count)
                return self.request_challenge(retry_count + 1)
            return None
    
    def solve_challenge(self, challenge):
        """Use LLM to solve the challenge with optimized prompt"""
        doc = challenge['doc']
        questions = challenge['questions']
        
        # Build ultra-optimized prompt
        prompt = f"""You are analyzing a mining industry document. Read CAREFULLY and answer with EXTREME PRECISION.

DOCUMENT:
{doc}

CRITICAL ANSWER RULES:
1. INFERENCE type → Give ONLY the technical term (1-4 words max)
   - Example: "chalcopyrite" NOT "chalcopyrite is a copper ore"
   - Example: "photosynthesis" NOT "the process of photosynthesis"

2. RECALL type → Copy EXACT text from document INCLUDING units
   - Example: "450 metric tons" NOT "450" or "450 tons"
   - Example: "24.19 million USD" NOT "24.2 million" or "24 million"

3. NUMERIC answers → Use EXACT precision from document
   - "24.19" is DIFFERENT from "24.2" or "24"
   - Include ALL decimal places as stated

4. COMPANY names → Use the PRIMARY name (first mention or most frequent)
   - Watch for aliases and abbreviations

5. COMPARISON questions (highest/most/largest) → Compare ALL entities mentioned
   - Don't assume - verify each one

6. IGNORE hypothetical statements, speculation, and "what if" scenarios

QUESTIONS:
"""
        for i, q in enumerate(questions, 1):
            prompt += f"Q{i} [TYPE: {q['type'].upper()}]: {q['question']}\n"
        
        prompt += "\nOUTPUT: Exactly 10 answers in format 'Q1: answer' (one per line, NO explanations, NO reasoning)"
        
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
                        'content': 'You are an expert document analyst specializing in mining industry reports. You extract precise information: single technical terms for inference questions, exact quotes with units for recall questions, and exact numeric values with full precision. You never round numbers or paraphrase.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.0,
                'max_tokens': 800,
                'top_p': 1.0
            }
            
            response = self.session.post(
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
            
            return answers if len(answers) == 10 else None
            
        except Exception as e:
            return None
    
    def parse_answers(self, text):
        """Parse LLM output with improved regex"""
        answers = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match Q1: answer or 1: answer or 1. answer
            match = re.match(r'^(?:Q|Question)?\s*\d+[:.)\s]+(.+)$', line, re.IGNORECASE)
            if match:
                answer = match.group(1).strip().strip('"\'`')
                answers.append(answer)
        
        return answers[:10]
    
    def submit_answers(self, challenge_id, answers, retry_count=0):
        """Submit answers with retry and backoff"""
        url = f"{self.api_url}/api/challenges/submit"
        
        payload = {
            'wallet': self.wallet,
            'challengeId': challenge_id,
            'answers': answers
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            data = response.json()
            
            if response.status_code == 200 and data.get('success'):
                score = data['score']
                total = data['total']
                failed = data.get('failedQuestions', [])
                
                self.stats['total_solves'] += 1
                self.stats['total_score'] += score
                if score == total:
                    self.stats['perfect_scores'] += 1
                
                self.stats['history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'score': score,
                    'failed': failed
                })
                
                # Keep only last 100 history entries
                if len(self.stats['history']) > 100:
                    self.stats['history'] = self.stats['history'][-100:]
                
                self.save_stats()
                
                # Get transaction signature for Solscan link
                tx_sig = data.get('txSignature')
                
                return True, score, total, failed, tx_sig
                
            elif 'rate limit' in str(data.get('error', '')).lower():
                if retry_count < 3:
                    wait = 10 * (retry_count + 1)
                    time.sleep(wait)
                    return self.submit_answers(challenge_id, answers, retry_count + 1)
            
            return False, 0, 10, [], None
                
        except Exception as e:
            if retry_count < 2:
                time.sleep(5)
                return self.submit_answers(challenge_id, answers, retry_count + 1)
            return False, 0, 10, [], None
    
    def get_leaderboard_rank(self, force=False):
        """Get current rank from leaderboard with caching"""
        now = time.time()
        
        # Cache for 30 seconds to avoid rate limit
        if not force and (now - self.last_rank_check) < 30:
            return self.cached_rank, self.cached_total
        
        try:
            response = self.session.get(f"{self.api_url}/api/leaderboard", timeout=10)
            if response.status_code == 200:
                data = response.json()
                miners = data.get('miners', data.get('leaderboard', []))
                
                for i, miner in enumerate(miners, 1):
                    wallet_addr = miner.get('wallet', miner.get('address', ''))
                    if wallet_addr == self.wallet:
                        self.cached_rank = i
                        self.cached_total = len(miners)
                        self.last_rank_check = now
                        return i, len(miners)
                
                self.cached_rank = None
                self.cached_total = len(miners)
                self.last_rank_check = now
                return None, len(miners)
        except:
            pass
        
        return self.cached_rank, self.cached_total
    
    def get_session_duration(self):
        """Calculate session duration"""
        if 'start_time' in self.stats:
            start = datetime.fromisoformat(self.stats['start_time'])
            duration = datetime.now() - start
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}m"
        return "N/A"
    
    def print_dashboard(self):
        """Print live dashboard header"""
        rank, total = self.get_leaderboard_rank()
        
        # Calculate stats
        solves = self.stats['total_solves']
        score = self.stats['total_score']
        perfect = self.stats['perfect_scores']
        avg = score / solves if solves > 0 else 0
        perfect_rate = (perfect / solves * 100) if solves > 0 else 0
        session_time = self.get_session_duration()
        
        # Build dashboard
        print("\n" + "╔" + "═" * 68 + "╗")
        
        # Line 1: Rank and Solves
        rank_str = f"#{rank}/{total}" if rank else f"Unranked/{total}" if total else "N/A"
        line1 = f"║ 🏆 Rank: {rank_str:<12} │ ⛏ Solves: {solves:<6} │ 📊 Avg: {avg:.1f}/10"
        line1 += " " * (68 - len(line1) + 1) + "║"
        print(line1)
        
        # Line 2: Perfect scores and session time
        line2 = f"║ 🎯 Perfect: {perfect} ({perfect_rate:.0f}%)"
        line2 += " " * (35 - len(line2))
        line2 += f"│ ⏱ Session: {session_time}"
        line2 += " " * (68 - len(line2) + 1) + "║"
        print(line2)
        
        print("╚" + "═" * 68 + "╝\n")
    
    def print_stats(self):
        """Print current statistics (legacy, kept for compatibility)"""
        self.print_dashboard()
    
    def mine_loop(self, auto_restart=True):
        """Main mining loop with live dashboard"""
        print(f"{'='*70}")
        print(f"{'COAL MINING BOT - OPTIMIZED':^70}")
        print(f"{'='*70}")
        print(f"Wallet: {self.wallet[:8]}...{self.wallet[-8:]}")
        print(f"Model: {self.llm_model}")
        print(f"Cooldown: {self.cooldown_between_solves}s")
        print(f"Auto-restart: {'ON' if auto_restart else 'OFF'}")
        print(f"{'='*70}")
        
        consecutive_failures = 0
        attempt = 0
        
        try:
            while True:
                attempt += 1
                
                # Show dashboard every solve
                self.print_dashboard()
                
                # Request challenge
                challenge = self.request_challenge()
                if not challenge:
                    consecutive_failures += 1
                    if consecutive_failures >= 10:
                        if not auto_restart:
                            print("\n✗ Too many failures. Stopping.")
                            break
                        print(f"\n⚠ {consecutive_failures} failures. Waiting 30s...")
                        time.sleep(30)
                        consecutive_failures = 0
                    else:
                        time.sleep(3)
                    continue
                
                cid = challenge['challengeId'][:10]
                epoch = challenge['epoch']
                print(f"[{attempt}] Challenge {cid}... Epoch {epoch}")
                
                # Solve
                print("🤖 Solving with LLM...", end="", flush=True)
                answers = self.solve_challenge(challenge)
                if not answers:
                    consecutive_failures += 1
                    print(f"\r✗ LLM failed" + " " * 30)
                    if consecutive_failures >= 10:
                        if not auto_restart:
                            break
                        print(f"⚠ Waiting 30s...")
                        time.sleep(30)
                        consecutive_failures = 0
                    continue
                print(f"\r✓ Solved!" + " " * 30)
                
                # Submit
                success, score, total, failed, tx_sig = self.submit_answers(challenge['challengeId'], answers)
                
                if success:
                    consecutive_failures = 0
                    emoji = "🎯" if score == 10 else "✓" if score >= 7 else "⚠"
                    print(f"{emoji} Score: {score}/{total}", end="")
                    
                    if failed:
                        print(f" | Failed: Q{', Q'.join(map(str, [f+1 for f in failed]))}", end="")
                    
                    if tx_sig:
                        print(f"\n   🔗 TX: https://solscan.io/tx/{tx_sig}")
                    else:
                        print()
                    
                    # Force rank update every 5 solves
                    if self.stats['total_solves'] % 5 == 0:
                        self.get_leaderboard_rank(force=True)
                else:
                    consecutive_failures += 1
                    print(f"✗ Submit failed")
                    if consecutive_failures >= 10:
                        if not auto_restart:
                            break
                        print(f"⚠ Waiting 30s...")
                        time.sleep(30)
                        consecutive_failures = 0
                
                # Cooldown
                print(f"⏳ Next solve in {self.cooldown_between_solves}s...")
                time.sleep(self.cooldown_between_solves)
                
        except KeyboardInterrupt:
            print("\n\n⛏ Mining stopped by user")
        
        self.print_dashboard()
        self.print_final_stats()
    
    def print_final_stats(self):
        """Print detailed final statistics"""
        print(f"\n{'='*70}")
        print(f"{'FINAL STATISTICS':^70}")
        print(f"{'='*70}")
        print(f"Total Solves: {self.stats['total_solves']}")
        print(f"Total Score: {self.stats['total_score']}")
        print(f"Perfect Scores (10/10): {self.stats['perfect_scores']}")
        
        if self.stats['total_solves'] > 0:
            avg = self.stats['total_score'] / self.stats['total_solves']
            perfect_rate = (self.stats['perfect_scores'] / self.stats['total_solves']) * 100
            print(f"Average Score: {avg:.2f}/10")
            print(f"Perfect Rate: {perfect_rate:.1f}%")
        
        # Recent performance
        if len(self.stats['history']) >= 10:
            recent = self.stats['history'][-10:]
            recent_avg = sum(h['score'] for h in recent) / len(recent)
            print(f"Last 10 Average: {recent_avg:.1f}/10")
        
        # Get final rank
        rank, total = self.get_leaderboard_rank(force=True)
        if rank:
            print(f"Final Rank: #{rank} / {total}")
        
        session_time = self.get_session_duration()
        print(f"Session Duration: {session_time}")
        
        print(f"{'='*70}\n")

if __name__ == "__main__":
    bot = CoalMiningBotOptimized()
    bot.mine_loop(auto_restart=True)
