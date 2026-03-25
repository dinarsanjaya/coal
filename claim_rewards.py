import requests
import json
import base64

try:
    # Try new solana-py v0.30+
    from solana.rpc.api import Client
    from solders.transaction import VersionedTransaction
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    SOLANA_NEW = True
except ImportError:
    try:
        # Try old solana-py
        from solana.rpc.api import Client
        from solana.transaction import Transaction
        from solana.keypair import Keypair
        from solana.publickey import PublicKey
        SOLANA_NEW = False
    except ImportError:
        print("✗ Solana library not installed")
        print("Install with: pip install solana")
        exit(1)

def claim_epoch_rewards(wallet_keypair, epoch):
    """Claim COAL rewards for a specific epoch"""
    
    api_url = "https://coalmine.fun"
    
    # Get wallet public key
    if SOLANA_NEW:
        wallet = str(wallet_keypair.pubkey())
    else:
        wallet = str(wallet_keypair.public_key)
    
    print(f"Claiming rewards for epoch {epoch}...")
    print(f"Wallet: {wallet}\n")
    
    try:
        # Request claim transaction from API
        response = requests.post(
            f"{api_url}/api/rewards/claim",
            json={"wallet": wallet, "epoch": epoch},
            timeout=30
        )
        
        if response.status_code != 200:
            data = response.json()
            error = data.get('error', 'Unknown error')
            print(f"✗ Claim request failed: {error}")
            if 'message' in data:
                print(f"  {data['message']}")
            return False
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✗ Claim failed: {data.get('message', 'Unknown error')}")
            return False
        
        # Get transaction
        tx_base64 = data['transaction']
        estimated_payout = data.get('estimated_payout_display', 'N/A')
        
        print(f"✓ Claim transaction received")
        print(f"  Estimated payout: {estimated_payout}")
        print(f"  Signing and submitting...\n")
        
        # Decode and sign transaction
        tx_bytes = base64.b64decode(tx_base64)
        
        if SOLANA_NEW:
            # New solana-py with solders
            tx = VersionedTransaction.from_bytes(tx_bytes)
            # Sign with keypair
            signed_tx = VersionedTransaction.populate(tx.message, [wallet_keypair])
            tx_serialized = bytes(signed_tx)
        else:
            # Old solana-py
            tx = Transaction.deserialize(tx_bytes)
            tx.sign(wallet_keypair)
            tx_serialized = tx.serialize()
        
        # Send to Solana
        connection = Client("https://api.mainnet-beta.solana.com")
        result = connection.send_raw_transaction(tx_serialized)
        
        if hasattr(result, 'value'):
            signature = result.value
        else:
            signature = result
        
        print(f"✓ Transaction submitted!")
        print(f"  Signature: {signature}")
        print(f"  View: https://solscan.io/tx/{signature}")
        
        # Wait for confirmation
        print(f"\n⏳ Waiting for confirmation...")
        try:
            connection.confirm_transaction(signature)
            print(f"✓ Rewards claimed successfully!")
        except:
            print(f"⚠ Confirmation timeout (transaction may still succeed)")
            print(f"  Check: https://solscan.io/tx/{signature}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error claiming rewards: {e}")
        import traceback
        traceback.print_exc()
        return False

def claim_all_unclaimed(wallet_keypair):
    """Claim all unclaimed rewards"""
    
    api_url = "https://coalmine.fun"
    
    if SOLANA_NEW:
        wallet = str(wallet_keypair.pubkey())
    else:
        wallet = str(wallet_keypair.public_key)
    
    try:
        # Get unclaimed rewards
        response = requests.get(f"{api_url}/api/rewards/unclaimed?wallet={wallet}", timeout=10)
        
        if response.status_code != 200:
            print("✗ Could not fetch unclaimed rewards")
            return
        
        data = response.json()
        unclaimed = data.get('unclaimed', [])
        
        if not unclaimed:
            print("No unclaimed rewards to claim")
            return
        
        print(f"Found {len(unclaimed)} epoch(s) with unclaimed rewards\n")
        
        for reward in unclaimed:
            epoch = reward['epoch']
            payout = reward.get('estimated_payout_display', 'N/A')
            
            print(f"--- Epoch {epoch} ({payout}) ---")
            success = claim_epoch_rewards(wallet_keypair, epoch)
            
            if success:
                print(f"✓ Epoch {epoch} claimed\n")
            else:
                print(f"✗ Epoch {epoch} failed\n")
            
            # Small delay between claims
            import time
            time.sleep(2)
        
        print("Done claiming rewards!")
        
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    print("=== COAL Rewards Claimer ===\n")
    print("⚠ WARNING: This script requires your PRIVATE KEY")
    print("⚠ Only use if you understand the security implications\n")
    
    choice = input("Continue? (yes/no): ").strip().lower()
    
    if choice != 'yes':
        print("Aborted")
        exit()
    
    print("\nEnter your Solana wallet private key:")
    print("(Base58 format or JSON array of bytes)")
    private_key = input("> ").strip()
    
    try:
        # Try to parse private key
        if private_key.startswith('['):
            # JSON array format
            key_bytes = json.loads(private_key)
            if SOLANA_NEW:
                keypair = Keypair.from_bytes(bytes(key_bytes))
            else:
                keypair = Keypair(bytes(key_bytes))
        else:
            # Base58 format
            if SOLANA_NEW:
                keypair = Keypair.from_base58_string(private_key)
            else:
                from base58 import b58decode
                keypair = Keypair(b58decode(private_key))
        
        wallet_addr = str(keypair.pubkey()) if SOLANA_NEW else str(keypair.public_key)
        print(f"\n✓ Wallet loaded: {wallet_addr}\n")
        
        # Ask for epoch or claim all
        print("Options:")
        print("1. Claim specific epoch")
        print("2. Claim all unclaimed epochs")
        
        option = input("\nChoose option (1 or 2): ").strip()
        
        if option == "1":
            epoch = int(input("Enter epoch number: "))
            claim_epoch_rewards(keypair, epoch)
        elif option == "2":
            claim_all_unclaimed(keypair)
        else:
            print("Invalid option")
    
    except Exception as e:
        print(f"✗ Error loading wallet: {e}")
        print("\nMake sure your private key is in correct format:")
        print("- Base58 string, or")
        print("- JSON array like [1,2,3,...]")
