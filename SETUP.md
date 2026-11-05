# Setup checklist

Repos, code, the first products and the daily task are done. What's left:

1. **Pages.** Settings → Pages → Source: **GitHub Actions**.
2. **Vault token.** github.com/settings/personal-access-tokens/new, fine-grained:
   - Repository access: **Only select repositories** → `pixelco-vault`
   - Permissions → Contents: **Read and write**
   - Expiration: 1 year (set a reminder to renew it)
3. **Secrets.** Settings → Secrets and variables → Actions → New repository secret:
   - `VAULT_TOKEN`: the token from step 2
   - `STRIPE_KEY`: your restricted Stripe key (sandbox `rk_test_...` first)
4. **Run.** Actions → **PixelCo business day** → **Run workflow**.
5. **Contact email.** Put it in `config.yaml` (or tell Claude), so the Contact page shows it.

## Going live with Stripe
After the sandbox test purchase works, finish verification on the live account. Then create the same restricted key there (four permissions) and replace `STRIPE_KEY`. Products made during testing will get new live checkouts automatically if you clear their `buy_url` in the vault state, or just let new products go live from then on.
