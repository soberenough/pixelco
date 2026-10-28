# PixelCo

A small online company run by AI agents. It started with $0. It makes templates, free tools and guides, sells through Stripe, and uses what it learns to grow.

Shop: https://soberenough.github.io/pixelco

## How a day works

| When | Who | What |
|---|---|---|
| Morning | Daily Claude session (scheduled task) | Reads the CEO's plan, makes the day's items, and drops them as JSON files on the `inbox` branch |
| After that | GitHub Actions, from `main` | Syncs sales, checks every inbox file with the gatekeeper, builds the ones that pass, creates Stripe checkouts, publishes the site, and plans tomorrow |

## The agents

| Agent | Job |
|---|---|
| CEO | Splits each day's work across lanes by what sells, shuts down lanes that don't, and grows output with cash |
| Writer, Builder, Maker | Guides, free offline tools, and downloadable kits |
| Gatekeeper | Rejects anything with scripts, trackers, outside URLs in tools, risky files, or bad prices |
| Cashier | Creates Stripe checkout links, with Stripe as merchant of record |
| Accountant | Books net revenue from PixelCo's own checkouts only |
| Marketer | Storefront, policy pages, sitemap and RSS feed |

## Safety design

- **Keys:** live only in GitHub secrets. The AI session never holds one.
- **Stripe key:** restricted to products, prices, payment links and reading checkouts. It can't move money.
- **Inbox:** read as data only. Nothing on the `inbox` branch is ever executed, and the workflow always runs from `main`.
- **Tools:** must run fully offline. A Content-Security-Policy on every tool page also blocks all network access in the visitor's browser.
- **Private data:** revenue, history and paid downloads live in the private `pixelco-vault` repo. Raw Stripe IDs are hashed before storage.
- **Customer data:** none. Stripe handles buyer details.

## Local test

```
pip install requests pyyaml
PIXELCO_STATE=/tmp/state.json python -m pixelco.run --inbox-dir path/to/inbox
python -m pixelco.check queue/*/*.json
```
