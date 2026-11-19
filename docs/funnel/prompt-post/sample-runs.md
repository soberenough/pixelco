# Test runs of the late-payment prompt (Claude, 2026-11-19)

Three made-up invoices, run through the prompt exactly as a buyer would.
Checks: right stage picked, all four facts present, one clear ask, under 120 words,
no "just checking in", no invented consequences, missing info gets asked for.

## Test A: 3 days late, warm tone, repeat client
Input: Dana · Brightleaf Studio · INV-104 · $850 USD · due Nov 3 · today Nov 6 ·
"logo refresh, delivered Oct 20" · Stripe link · no late fee · nothing sent yet · repeat client · warm

**Output**
1. Stage 1, friendly nudge: 3 days late and nothing sent yet, so it probably slipped through.
2. Subject: Invoice INV-104 ($850): quick reminder
3. Email:
> Hi Dana,
>
> A quick reminder that invoice INV-104 for $850 (logo refresh, delivered Oct 20) was due on November 3. I've put the payment link below so it's easy to find:
> [Stripe link]
>
> Could you let me know if it's on its way this week? Hope the new logo is treating you well!
>
> Thanks,
> [Your name]
4. Text: "Hi Dana, a friendly reminder that invoice INV-104 ($850) was due Nov 3. Here's the payment link: [link]. Could you let me know when it's sent?"
5. Next: if it isn't paid by Nov 10, send stage 2. It restates the facts and asks for a specific payment date.

## Test B: 40 days late, direct tone, two reminders already sent, contract late fee
Input: Marcus · Halden Logistics · #2291 · $2,400 USD · due Oct 10 · today Nov 19 ·
"warehouse dashboard build, delivered Sep 26" · bank details on invoice · 1.5%/month after 30 days ·
friendly email Oct 15, firm follow-up Oct 28 · biggest client · direct

**Output**
1. Stage 3, pause notice: 40 days late, after two unanswered reminders.
2. Subject: Invoice #2291 ($2,400): 40 days overdue, work pausing Nov 26
3. Email:
> Hi Marcus,
>
> Invoice #2291 for $2,400 (warehouse dashboard build) was due on October 10 and is now 40 days overdue. Payment details are on the attached invoice.
>
> As our contract states, a late fee of 1.5% per month applies after 30 days. I'll also need to pause new work on November 26 until the balance is cleared.
>
> Please send payment, or reply with a firm payment date, by November 25.
>
> Regards,
> [Your name]
4. Text: "Marcus, invoice #2291 ($2,400) is 40 days overdue. Please send payment or a firm date by Nov 25, as new work pauses on Nov 26."
5. Next: if there's no payment by Nov 26 (the pause date, 47 days late), send stage 4. It will only name a next step you've confirmed you'll take.

## Test C: missing information
Input: same as A, but "How to pay" was left as [PAYMENT LINK / BANK DETAILS ...]

**Output**
> Before I write this: how should Dana pay? Send me the payment link or bank details,
> or say "see attached invoice" if the invoice already has them.

## Results
| Check | A | B | C |
|---|---|---|---|
| Right stage | ✓ 1 | ✓ 3 | n/a |
| Invoice #, amount, due date, how to pay | ✓ | ✓ | n/a |
| One specific ask | ✓ | ✓ | n/a |
| Email under 120 words | ✓ | ✓ | n/a |
| No "just checking in" / no invented threats | ✓ | ✓ (fee comes from the contract) | n/a |
| Asks for missing info | n/a | n/a | ✓ |
