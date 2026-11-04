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
After the sandbox test purchase works, finish verification on the live account. Then create the same restricted key there (four permissions: Products write, Prices write, Payment Links write, Checkout Sessions read) and replace `STRIPE_KEY` with the `rk_live_...` key.

Nothing else is needed. On the first run with a live key, PixelCo switches over by itself:
- every product gets a new live checkout link, and its download moves to a new secret folder (the old test links still exist in Stripe test mode, so the old folder is retired to stop free test-card downloads),
- test-mode sales move out of revenue into `treasury.test_revenue`, so the books only count real money,
- lane counters restart, so the CEO's "no sales" shutdown clock starts on the live date.

If the key is rejected (wrong key, or a missing permission), nothing is changed and the run records an alert. If the live account refuses a checkout (for example, Managed Payments isn't enabled for live), the product shows "Checkout opens soon" and the run records an alert naming the Stripe error.

Each switch of Stripe mode moves every download to a new secret folder, so download pages from before the switch stop working. That's fine for the one-time move to live; avoid switching back and forth once real customers have bought.

Optional: in Stripe **test** mode, deactivate the old Payment Links. If you use a tip link (`support_link_id` in `config.yaml`), replace it with a live one.
