import requests
import json

def get_coal_quote(sol_amount):
    """Get quote for SOL -> COAL swap via Jupiter"""
    
    # Token mints
    SOL_MINT = "So11111111111111111111111111111111111111112"  # Wrapped SOL
    COAL_MINT = "4kaN4oQMs4tcu7yLedFsSyuAUtmYgv9ufvt3ZjHwpump"
    
    # Convert SOL to lamports (1 SOL = 1,000,000,000 lamports)
    lamports = int(sol_amount * 1_000_000_000)
    
    # Jupiter Lite API quote endpoint
    url = "https://lite-api.jup.ag/swap/v1/quote"
    
    params = {
        'inputMint': SOL_MINT,
        'outputMint': COAL_MINT,
        'amount': lamports,
        'swapMode': 'ExactIn',
        'slippageBps': 5000  # 50% slippage (recommended for low liquidity)
    }
    
    try:
        print(f"Getting quote for {sol_amount} SOL -> COAL...")
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"✗ Quote failed: {response.status_code}")
            print(response.text)
            return None
        
        quote = response.json()
        
        # Parse output amount (COAL has 6 decimals)
        out_amount_raw = int(quote['outAmount'])
        out_amount_coal = out_amount_raw / 1_000_000
        
        print(f"\n✓ Quote received:")
        print(f"  Input: {sol_amount} SOL")
        print(f"  Output: {out_amount_coal:,.0f} COAL")
        print(f"  Price impact: {quote.get('priceImpactPct', 'N/A')}%")
        print()
        
        # Check if enough for mining tiers
        if out_amount_raw >= 1_000_000_000000:
            tier = 3
            print(f"✓ Tier 3 (1M+ COAL) - 3 points per solve")
        elif out_amount_raw >= 500_000_000000:
            tier = 2
            print(f"✓ Tier 2 (500k+ COAL) - 2 points per solve")
        elif out_amount_raw >= 250_000_000000:
            tier = 1
            print(f"✓ Tier 1 (250k+ COAL) - 1 point per solve")
        else:
            print(f"⚠ Not enough COAL for mining (need 250k minimum)")
            print(f"  Try increasing SOL amount")
            return None
        
        return quote
        
    except Exception as e:
        print(f"✗ Error getting quote: {e}")
        return None

def estimate_sol_needed_for_tier(tier):
    """Estimate SOL needed for each tier"""
    
    # Try different amounts to find what gives target COAL
    targets = {
        1: 250_000_000000,  # 250k COAL
        2: 500_000_000000,  # 500k COAL
        3: 1_000_000_000000  # 1M COAL
    }
    
    target_raw = targets.get(tier)
    if not target_raw:
        print("Invalid tier (use 1, 2, or 3)")
        return
    
    target_display = target_raw / 1_000_000
    
    print(f"\nFinding SOL amount needed for Tier {tier} ({target_display:,.0f} COAL)...")
    print("Testing different amounts...\n")
    
    # Binary search for right amount
    test_amounts = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
    
    for sol_amt in test_amounts:
        quote = get_coal_quote(sol_amt)
        if quote:
            out_raw = int(quote['outAmount'])
            if out_raw >= target_raw:
                print(f"\n✓ Recommended: ~{sol_amt} SOL for Tier {tier}")
                return sol_amt
    
    print(f"\n⚠ May need more than 5 SOL for Tier {tier}")
    print("Try manually with higher amounts")

if __name__ == "__main__":
    print("=== COAL Purchase Helper ===\n")
    print("This script helps you estimate how much SOL you need to buy COAL.\n")
    print("Choose an option:")
    print("1. Get quote for specific SOL amount")
    print("2. Estimate SOL needed for mining tier")
    print()
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        sol_amount = float(input("Enter SOL amount: "))
        get_coal_quote(sol_amount)
    elif choice == "2":
        tier = int(input("Enter target tier (1, 2, or 3): "))
        estimate_sol_needed_for_tier(tier)
    else:
        print("Invalid choice")
    
    print("\n" + "="*50)
    print("To actually buy COAL:")
    print("1. Use Jupiter swap UI: https://jup.ag/swap/SOL-COAL")
    print("2. Or use Solana wallet with Jupiter integration")
    print("3. COAL mint: 4kaN4oQMs4tcu7yLedFsSyuAUtmYgv9ufvt3ZjHwpump")
