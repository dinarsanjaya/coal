import requests
import json

def check_leaderboard(wallet=None, limit=50):
    """Check COAL mining leaderboard and wallet rank"""
    
    api_url = "https://coalmine.fun"
    
    # Try to get leaderboard
    try:
        # Check if there's a leaderboard endpoint
        endpoints_to_try = [
            f"{api_url}/api/leaderboard",
            f"{api_url}/api/stats/leaderboard",
            f"{api_url}/api/miners/leaderboard",
        ]
        
        leaderboard_data = None
        
        for endpoint in endpoints_to_try:
            try:
                response = requests.get(endpoint, timeout=10)
                if response.status_code == 200:
                    leaderboard_data = response.json()
                    print(f"✓ Found leaderboard at: {endpoint}\n")
                    break
            except:
                continue
        
        if not leaderboard_data:
            print("⚠ Leaderboard endpoint not found")
            print("Trying alternative: checking wallet stats directly...\n")
            
            if wallet:
                check_wallet_stats(wallet)
            return
        
        # Display leaderboard
        print("=== COAL Mining Leaderboard ===\n")
        
        if isinstance(leaderboard_data, dict):
            miners = leaderboard_data.get('miners', leaderboard_data.get('leaderboard', []))
            current_epoch = leaderboard_data.get('epoch', 'N/A')
            print(f"Current Epoch: {current_epoch}\n")
        else:
            miners = leaderboard_data
        
        # Show top miners
        print(f"{'Rank':<6} {'Wallet':<45} {'Solves':<8} {'Score':<8} {'Avg':<6}")
        print("-" * 80)
        
        wallet_found = False
        wallet_rank = None
        
        for i, miner in enumerate(miners[:limit], 1):
            wallet_addr = miner.get('wallet', miner.get('address', 'N/A'))
            solves = miner.get('solves', miner.get('total_solves', 0))
            score = miner.get('score', miner.get('total_score', 0))
            avg = score / solves if solves > 0 else 0
            
            # Truncate wallet for display
            wallet_display = wallet_addr[:8] + "..." + wallet_addr[-8:] if len(wallet_addr) > 20 else wallet_addr
            
            marker = ""
            if wallet and wallet_addr == wallet:
                marker = " ← YOU"
                wallet_found = True
                wallet_rank = i
            
            print(f"{i:<6} {wallet_display:<45} {solves:<8} {score:<8} {avg:<6.1f}{marker}")
        
        print()
        
        # Show wallet rank if provided
        if wallet:
            if wallet_found:
                print(f"✓ Your rank: #{wallet_rank}")
            else:
                print(f"⚠ Your wallet not in top {limit}")
                print(f"  Wallet: {wallet}")
                print(f"  Keep mining to climb the leaderboard!")
        
    except Exception as e:
        print(f"✗ Error fetching leaderboard: {e}")
        print("\nTrying wallet stats instead...\n")
        if wallet:
            check_wallet_stats(wallet)

def check_wallet_stats(wallet):
    """Check individual wallet mining stats"""
    
    api_url = "https://coalmine.fun"
    
    endpoints_to_try = [
        f"{api_url}/api/stats?wallet={wallet}",
        f"{api_url}/api/miners/{wallet}",
        f"{api_url}/api/wallet/{wallet}/stats",
    ]
    
    for endpoint in endpoints_to_try:
        try:
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                print("=== Your Mining Stats ===\n")
                print(f"Wallet: {wallet}")
                
                # Try to extract stats (format may vary)
                if isinstance(data, dict):
                    solves = data.get('solves', data.get('total_solves', 'N/A'))
                    score = data.get('score', data.get('total_score', 'N/A'))
                    epoch = data.get('epoch', data.get('current_epoch', 'N/A'))
                    tier = data.get('tier', 'N/A')
                    
                    print(f"Total Solves: {solves}")
                    print(f"Total Score: {score}")
                    
                    if isinstance(solves, int) and isinstance(score, int) and solves > 0:
                        avg = score / solves
                        print(f"Average: {avg:.1f}/10")
                    
                    print(f"Current Epoch: {epoch}")
                    print(f"Tier: {tier}")
                
                return
        except:
            continue
    
    print("⚠ Could not fetch wallet stats")
    print("The API might not have public stats endpoints")

def check_unclaimed_rewards(wallet):
    """Check unclaimed COAL rewards"""
    
    api_url = "https://coalmine.fun"
    
    try:
        response = requests.get(f"{api_url}/api/rewards/unclaimed?wallet={wallet}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n=== Unclaimed Rewards ===\n")
            print(f"Wallet: {data.get('wallet', wallet)}")
            print(f"Current Epoch: {data.get('current_epoch', 'N/A')}")
            
            unclaimed = data.get('unclaimed', [])
            
            if unclaimed:
                print(f"\nYou have {len(unclaimed)} epoch(s) with unclaimed rewards:\n")
                
                for reward in unclaimed:
                    epoch = reward.get('epoch')
                    payout = reward.get('estimated_payout_display', 'N/A')
                    solves = reward.get('user_effective_solves', 'N/A')
                    
                    print(f"  Epoch {epoch}: {payout} ({solves} effective solves)")
                
                total = data.get('total_unclaimed_display', 'N/A')
                print(f"\nTotal unclaimed: {total}")
                print("\nTo claim: python claim_rewards.py")
            else:
                print("No unclaimed rewards")
        elif response.status_code == 429:
            print("⚠ Rate limited. Try again in a moment.")
        else:
            print(f"⚠ Could not fetch unclaimed rewards (status: {response.status_code})")
            
    except Exception as e:
        print(f"✗ Error checking rewards: {e}")

if __name__ == "__main__":
    # Load wallet from config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        wallet = config['wallet']
    except:
        wallet = None
    
    print("=== COAL Mining Rank Checker ===\n")
    
    # Check leaderboard
    check_leaderboard(wallet, limit=50)
    
    # Check unclaimed rewards if wallet available
    if wallet:
        check_unclaimed_rewards(wallet)
