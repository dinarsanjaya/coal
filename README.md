# COAL Mining Bot ⛏

Bot untuk mining COAL dengan LLM. Bot ini pakai AI untuk jawab pertanyaan tentang dokumen mining companies dan dapat COAL rewards.

## Cara Kerja

COAL mining bukan mining GPU biasa - ini pakai LLM untuk:
1. Baca dokumen panjang tentang fictional mining companies
2. Jawab 10 pertanyaan tentang dokumen tersebut
3. Dapat COAL berdasarkan jawaban yang benar

## Requirements

1. **Solana Wallet** dengan minimal **250,000 COAL**
   - Tier 1 (250k COAL): 1 point per solve
   - Tier 2 (500k COAL): 2 points per solve
   - Tier 3 (1M COAL): 3 points per solve

2. **OpenAI API Key** (atau LLM provider lain yang compatible)
   - Butuh model yang bagus untuk reading comprehension
   - Recommended: GPT-4 atau Claude

3. **Python 3.7+**

## Setup

1. **Install dependencies:**
```cmd
pip install requests
```

2. **Edit config.json:**
```json
{
  "api_url": "https://coalmine.fun",
  "wallet": "YOUR_SOLANA_WALLET_ADDRESS",
  "llm_api_key": "YOUR_OPENAI_API_KEY",
  "llm_model": "gpt-4"
}
```

3. **Pastikan punya COAL di wallet:**
   - Minimal 250,000 COAL untuk bisa mining
   - Beli COAL via Jupiter swap (SOL → COAL)
   - COAL mint: `4kaN4oQMs4tcu7yLedFsSyuAUtmYgv9ufvt3ZjHwpump`

## Cara Pakai

```cmd
cd mining-bot
python bot.py
```

Bot akan:
- Request challenge dari COAL API
- Pakai LLM untuk solve pertanyaan
- Submit jawaban
- Repeat sampai di-stop atau error

## Stop Mining

Tekan `Ctrl+C`

## Stats

Bot akan show:
- Score per solve (X/10)
- Transaction signature (on-chain proof)
- Failed questions (kalau ada)
- Total solves & average score

## Claiming Rewards

Setelah epoch selesai, claim rewards dengan script terpisah atau manual via API.

## Tips

- Pakai model LLM yang kuat (GPT-4 recommended)
- Bot auto-retry kalau ada cooldown
- Akan stop kalau 5x gagal berturut-turut
- Check balance COAL sebelum mulai mining
