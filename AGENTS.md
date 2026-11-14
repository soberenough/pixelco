# Agent notes

Start with [README.md](README.md). The daily maker session brief in [DAILY.md](DAILY.md) applies only to writing queue files on the `inbox` branch.

## ECC for Claude Code

This repository enables the official ECC plugin for Claude Code (`ecc@ecc`) from [affaan-m/ECC](https://github.com/affaan-m/ECC) only, via `.claude/settings.json`. Claude Code should use ECC's **code-reviewer** and **security-review** agents on pull requests.

Install ECC only from that official GitHub repository, the official npm packages (`ecc-universal`, `ecc-agentshield`), or the plugin slug `ecc@ecc`. Third-party re-uploads and unofficial mirrors may contain malware.

Owner approval is still required for merges, deployments, and any payment or Stripe changes. Do not merge, deploy, or change payment code without the owner's explicit OK.
