import requests
import json

def check_coal_balance(wallet):
    """Check COAL balance using Solana RPC"""
    
    # COAL token mint address
    COAL_MINT = "4kaN4oQMs4tcu7yLedFsSyuAUtmYgv9ufvt3ZjHwpump"
    
    # Use public Solana RPC
    rpc_url = "https://api.mainnet-beta.solana.com"
    
    # Get token accounts for wallet
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet,
            {"mint": COAL_MINT},
            {"encoding": "jsonParsed"}
        ]
    }
    
    try:
        response = requests.post(rpc_url, json=payload)
        data = response.json()
        
        if 'result' in data and data['result']['value']:
            # Found COAL token account
            token_account = data['result']['value'][0]
            balance_info = token_account['account']['data']['parsed']['info']['tokenAmount']
            
            raw_balance = int(balance_info['amount'])
            decimals = balance_info['decimals']
            ui_balance = balance_info['uiAmount']
            
            print(f"✓ COAL Balance Found!")
            print(f"  Wallet: {wallet}")
            print(f"  Balance: {ui_balance:,.0f} COAL")
            print(f"  Raw: {raw_balance} (decimals: {decimals})")
            print()
            
            # Check tier
            if raw_balance >= 1_000_000_000000:
                tier = 3
                points = 3
            elif raw_balance >= 500_000_000000:
                tier = 2
                points = 2
            elif raw_balance >= 250_000_000000:
                tier = 1
                points = 1
            else:
                tier = 0
                points = 0
                print(f"⚠ INSUFFICIENT COAL!")
                print(f"  Need: 250,000 COAL minimum")
                print(f"  Have: {ui_balance:,.0f} COAL")
                print(f"  Short: {250_000 - ui_balance:,.0f} COAL")
                return False
            
            print(f"✓ Mining Tier: {tier}")
            print(f"  Points per solve: {points}")
            return True
            
        else:
            print(f"✗ No COAL token found in wallet")
            print(f"  Wallet: {wallet}")
            print(f"  COAL Mint: {COAL_MINT}")
            print()
            print(f"You need to buy COAL first!")
            return False
            
    except Exception as e:
        print(f"✗ Error checking balance: {e}")
        return False

if __name__ == "__main__":
    # Load wallet from config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    wallet = config['wallet']
    print(f"Checking COAL balance...\n")
    check_coal_balance(wallet)
