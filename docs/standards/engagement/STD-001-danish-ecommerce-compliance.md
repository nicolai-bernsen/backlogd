---
id: STD-001
title: Danish e-commerce compliance (haekl.dk webshop)
status: Accepted
date: 2026-05-31
problem: NB-400
supersedes: ~
superseded-by: ~
assertion: Every change touching payments, checkout, pricing, order state, file delivery, customer data, or invoicing for haekl.dk obeys rules R1-R9 below; a MUST tripwire (R1 business-agreement payments, R2 webhook-is-truth, R3 25% moms + invoice, R5 digital-content withdrawal consent, R6 signed expiring file URLs) is a hard block — cite the specific rule id and its fix, never just "non-compliant".
applies-to:
  domains: [payments, checkout, pricing, order-state, file-delivery, customer-data, invoicing, compliance]
  file-patterns: ["**"]
  decision-types: [payments, payment-provider, order-state, vat, invoicing, file-delivery, pii, consumer-rights, pricing]
rules:
  R1: "MUST | Card + MobilePay run only through MobilePay-via-Stripe or MobilePay MyShop; a personal/private MobilePay account is never used to receive shop payments. | Route payments through a Stripe account or a MyShop business agreement; remove any flow that tells a customer to transfer to a personal MobilePay number."
  R2: "MUST | An order becomes paid solely on a signature-verified, idempotent provider webhook (checkout.session.completed or equivalent); the browser redirect never grants fulfilment or downloads. | Set paid and issue downloads only from the verified webhook handler (verify the signature, dedupe on event id); never from the client-side return URL."
  R3: "MUST | Charge 25% Danish VAT on all B2C sales; each order persists net/VAT/gross per line and produces an invoice (seller name + CVR/VAT no., sequential invoice number, date, line items, total) retained per Bogforingsloven. | Model net/vat/gross per line on the order and generate + store an invoice artifact carrying the required fields and a sequential number."
  R4: "SHOULD | Below the EU 10,000 EUR/yr cross-border B2C threshold, charge Danish VAT and nothing else; do not pre-build OSS rate-by-destination logic. | Charge Danish VAT only; add OSS destination-rate logic later, when the threshold is actually in sight."
  R5: "MUST | Physical goods carry a 14-day fortrydelsesret; for digital content delivered immediately the right is lost only on express prior consent acknowledged before download, so checkout captures that consent on any cart containing a digital line. | Record an explicit consent flag + timestamp before generating a download grant for any digital-line purchase."
  R6: "MUST | Pattern files live in private object storage; access is via per-order, time-limited signed URLs with a download cap; no public/guessable paths, and raw object keys never reach the client. | Keep the bucket private and serve files via signed, expiring URLs scoped to a download grant; never expose a public path or a raw object key."
  R7: "MUST | Store only the PII needed to fulfil + invoice; per MobilePay terms a customer phone number tied to MobilePay is never stored beyond the transaction. | Remove any MobilePay msisdn column; justify each retained PII column by a fulfilment/invoicing need."
  R8: "MUST | Use a hosted payment surface (Stripe-hosted Checkout or Elements); the app never sees or stores PAN/CVC. | Move card entry onto Stripe-hosted Checkout/Elements so no raw card data reaches the app."
  R9: "MUST | All prices displayed to consumers are totals incl. 25% VAT. | Render consumer-facing prices as VAT-inclusive totals."
---

**STD-001 — Danish e-commerce compliance (haekl.dk webshop)**

- **Status:** Accepted _(2026-05-31)_ · **Problem:** [NB-400](https://linear.app/nicolai-bernsen/issue/NB-400)
- **Type:** per-engagement, agent-readable standard · **Enforced by:** the reviewer
- **Decision (TL;DR):** the haekl.dk shop's binding engineering rules for payments,
  checkout, VAT/invoicing, order state, file delivery and customer data are **R1–R9**
  below. The reviewer reads them index-first (via
  [`docs/standards/index.json`](../index.json)) and **blocks** any problem or change that
  trips a **MUST** rule — citing the specific rule id **and its fix**.

> Not legal advice. These are the binding **engineering** rules for this shop; the owner's
> accountant confirms specifics (CVR/VAT, bogføring, OSS). The reviewer blocks any problem
> or change that violates a MUST.

## What this is (and why it is not an ADR)

This is the first **per-engagement standard** — the _domain_ rules for _this instance's_
product (a Danish webshop), as distinct from the framework **ADRs** (`ADR-*.md`) that
govern backlogd itself. It is the "domain DoD" half of
[ADR-004](../adrs/ADR-004-backlogd-identity.md)'s _value = specialists × standards_:
the framework stays domain-agnostic, and an instance earns its value by adding standards
like this one.

It lives under `docs/standards/engagement/` and is named `STD-NNN-<slug>.md`. It is indexed
by the **same** machinery as the ADRs — `python scripts/standards_index.py` reads its
front-matter into [`docs/standards/index.json`](../index.json), and the drift test
(`scripts/test_standards_index.py`) fails CI if the committed index diverges from this file.
So **front-matter is the single source of truth**: edit a rule here, then regenerate the
index in the same change.

## The rule grammar — why rule IDs and fixes are first-class

A framework ADR carries one `assertion`. A per-engagement standard like this one carries
**many numbered rules** — each with its own **MUST/SHOULD level**, a checkable
**assertion**, and a concrete **fix**. They are authored in the front-matter `rules:` block,
one line per rule:

```yaml
rules:
  R2: "MUST | <assertion> | <fix>"
```

The index explodes each line into `{"id": "R2", "level": "MUST", "assertion": …, "fix": …}`
so the reviewer can do the thing AC1/AC4 of NB-400 require: when a change trips a rule,
**name the rule id (R2) and its fix**, not a bare "non-compliant". A **MUST** rule is a
blocking tripwire; a **SHOULD** rule is advisory (the reviewer flags it, does not block on it
alone).

## Scope

Applies to every problem touching **payments, checkout, pricing, order state, file
delivery, customer data, or invoicing** for haekl.dk. (This is the `applies-to` scope in the
front-matter; a change outside it is out of scope for this standard.)

## Rules

### R1 — Payments only via a business agreement (MUST)

Card + MobilePay must run through **MobilePay-via-Stripe** or **MobilePay MyShop**. A
personal/private MobilePay account MUST NOT be used to receive shop payments — it violates
MobilePay's terms, breaks bogføring/moms documentation, and has no integration surface.

- **Verify:** payment config references a Stripe account or a MyShop business agreement; no
  flow instructs a customer to transfer to a personal number.
- **Fix:** route payments through a Stripe account or a MyShop business agreement; remove
  any flow that tells a customer to transfer to a personal MobilePay number.

### R2 — The paid-webhook is the only source of truth (MUST)

An order becomes `paid` solely on a signature-verified, idempotent provider webhook
(`checkout.session.completed` / equivalent). The browser redirect MUST NOT grant fulfilment
or downloads.

- **Verify:** no code path sets `paid`/issues a download from a client-side return URL;
  webhook handler verifies signature and is idempotent on event id.
- **Fix:** set `paid` and issue downloads only from the verified webhook handler (verify the
  signature, dedupe on event id); never from the client-side return URL.

### R3 — 25% moms + valid invoice on every sale (MUST)

Charge Danish VAT (25%) on all B2C sales. Each order produces an invoice with: seller name +
CVR/VAT no., sequential invoice number, date, line items with net/VAT/gross, total. Records
retained per Bogføringsloven.

- **Verify:** order persists net/vat/gross per line; invoice artifact generated and stored.
- **Fix:** model net/vat/gross per line on the order and generate + store an invoice artifact
  carrying the required fields and a sequential number.

### R4 — OSS only above threshold (SHOULD)

Below €10,000/yr cross-border B2C across the EU, charge Danish VAT and do nothing else. Build
OSS rate-by-destination logic only when that threshold is in sight. Don't pre-build it.

- **Fix:** charge Danish VAT only; add OSS destination-rate logic later, when the threshold
  is actually in sight.

### R5 — Right of withdrawal handled correctly (MUST)

Physical goods: 14-day fortrydelsesret. Digital content delivered immediately: the right is
lost **only if** the customer gives express prior consent and acknowledges losing it before
download — so checkout MUST capture that consent on any cart containing a digital line.

- **Verify:** digital purchase flow records an explicit consent flag + timestamp before
  generating a download grant.
- **Fix:** record an explicit consent flag + timestamp before generating a download grant for
  any digital-line purchase.

### R6 — Files served only via signed, expiring URLs (MUST)

Pattern PDFs live in private object storage. Access is via per-order, time-limited signed
URLs with a download cap. No public/guessable paths. Raw object keys never reach the client.

- **Verify:** storage bucket is private; delivery issues signed URLs scoped to a download
  grant.
- **Fix:** keep the bucket private and serve files via signed, expiring URLs scoped to a
  download grant; never expose a public path or a raw object key.

### R7 — Minimal PII; no MobilePay data retention (MUST)

Store the minimum needed to fulfil + invoice. Per MobilePay terms, customer phone numbers
tied to MobilePay MUST NOT be stored beyond the transaction.

- **Verify:** schema has no MobilePay msisdn column; PII columns justified by
  fulfilment/invoicing.
- **Fix:** remove any MobilePay msisdn column; justify each retained PII column by a
  fulfilment/invoicing need.

### R8 — No raw card data; hosted payment surface (MUST)

Use Stripe-hosted Checkout or Elements. The app never sees or stores PAN/CVC.

- **Fix:** move card entry onto Stripe-hosted Checkout/Elements so no raw card data reaches
  the app.

### R9 — Consumer prices shown incl. VAT (MUST)

All prices displayed to consumers are totals incl. 25% VAT.

- **Fix:** render consumer-facing prices as VAT-inclusive totals.

## Reviewer behaviour

Block + request changes if a problem or change: routes payment outside a business agreement
(**R1**), marks paid from a client redirect (**R2**), omits VAT/invoice modelling (**R3**),
skips withdrawal-consent capture on a digital cart (**R5**), or exposes unsigned/public file
URLs (**R6**). These are the missing-standard tripwires; surfacing one is the expected demo
moment. The block message **names the rule id and its fix** (drawn from the `rules` block
above), so the developer knows exactly what to change — not just that it is "non-compliant".

## References

EU OSS / €10k threshold · Bogføringsloven (retention) · Forbrugeraftaleloven (fortrydelsesret,
digital-content consent) · MobilePay business-agreement + data terms · Stripe
MobilePay/Checkout.

---
_Refs: NB-400 · indexed by `scripts/standards_index.py` into
[`docs/standards/index.json`](../index.json); the reviewer consults it index-first
([`agents/reviewer.md`](../../../agents/reviewer.md), [`skills/reviewer/SKILL.md`](../../../skills/reviewer/SKILL.md))._
