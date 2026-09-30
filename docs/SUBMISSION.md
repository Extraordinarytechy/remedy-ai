# RemedyAI: find the free repair or refund you may still be owed after your warranty ends

**Live:** https://d1fnfajqesgvsl.cloudfront.net (no sign-up) · **Code:** https://github.com/Extraordinarytechy/remedy-ai · **Category:** `#daily-life-enhancement` · **Lane:** `#startups`

## The problem, in one real example

Apple runs a free repair program for iPhone 14 Plus rear cameras that show no preview. It covers units made between April 10, 2023 and April 28, 2024, for **three years from first retail sale**, and Apple says people who already paid for that repair can ask for a refund ([Apple](https://support.apple.com/iphone-14-plus-service-program-for-rear-camera-issue)). The standard warranty on the same phone is one year.

So an owner whose camera fails at month 30 is out of warranty and still entitled to a free repair, and nothing tells them. The windows for the earliest affected units have started closing: a phone first sold in April 2023 lost its free repair in April 2026. The last ones close around mid-2027.

That gap is not specific to Apple. Some credit cards add a year to the manufacturer warranty. In the UK, the retailer can owe a repair or replacement for up to 6 years. Each route has its own rules, dates and caveats, and each lives on a different page.

## What RemedyAI does

You describe what broke (optionally with a receipt photo and a photo of the fault). RemedyAI checks it against the **published source** for each route it knows about and returns, for every match:

- **why it matched**, with the dates it measured (the claim date, not just the failure date)
- **what you will need**, copied from the source
- **what could stop it**, also from the source (for Apple: a cracked back must be fixed first and may cost money)
- a **timeline**: purchase, failure and claim dates, and the deadline for each option
- a **claim PDF** and a draft letter

If a receipt photo was read, RemedyAI also **checks it against what you typed**. A receipt priced in dollars for a claim entered as a UK purchase holds the UK option and the claim PDF until you confirm where you bought it; a different date or store on the receipt is shown as a warning.

If no source covers the case, it says so: `NO VERIFIED COVERAGE FOUND`, plus the sources it checked that did not apply and why.

Six routes today, from four kinds of source:

| Route | Source | Status in RemedyAI |
| --- | --- | --- |
| Apple One (1) Year Limited Warranty (U.S.; iPhone, iPad and other iOS devices) | Apple | Covers new launches such as iPhone 18 Pro (on sale September 18, 2026): defects for one year from purchase, claimed during the year. Accidental damage is not covered |
| Mac mini (2023, M2) no-power program | Apple | Active, on Apple's index since June 2025; serial check required. Found missing on 2026-09-30, verified by a person and added |
| iPhone 14 Plus rear camera program | Apple | Active; requires Apple's serial check, so RemedyAI never says "eligible", only "possible: check your serial number" |
| iPhone 12 / 12 Pro no-sound program | Apple | Page still online, **not on Apple's index**; nearly every unit is past its window |
| Visa Infinite extended warranty (+1 year on warranties of 3 years or less) | Visa | Issuer's Guide to Benefits governs; RemedyAI shows only what Visa's page states |
| UK consumer rights on faulty goods (6 years, 5 in Scotland) | GOV.UK | Includes the burden-of-proof shift after 6 months |

## What makes it different: Source Watch

A static warranty database goes stale quietly. We found this out the hard way (see "What went wrong"), so RemedyAI now checks its own sources every day:

- **EventBridge Scheduler** runs a Lambda at 06:00 UTC.
- It fetches every source page plus Apple's [service-program index](https://support.apple.com/service-programs), hashes the visible text, and **stores a dated snapshot in S3 whenever a page changes**.
- It records, per source: HTTP status, whether an Apple program is still listed on the index, when the text last changed, and which programs appeared or disappeared from the index since the previous run.
- The API reads that status on every evaluation. A route whose source page is unreachable, or whose Apple program has left the index, is **downgraded to "Source changed: re-verify first"** instead of being shown as a match. If a page's text changes after a person last checked it, the route carries a warning with both dates.

The Source Watch table is on the home page, so anyone can see when each source was last checked by a person and by the machine.

It also compares Apple's list with the corpus and publishes a **gap alert**: any repair program Apple lists that RemedyAI has no record for. That check exists because the Mac mini (2023) no-power program had been on Apple's list since June 2025 without a RemedyAI record; a person verified its page and added it on 2026-09-30.

It has already done its job, and taught us something. On 2026-09-30 it recorded that the text of Visa's Visa Infinite page had changed since the last human check. A person re-read the page: the Extended Warranty wording (one extra year on eligible warranties of 3 years or less) was unchanged, so the record's human-check date was updated. The page then changed again the same day, for reasons unrelated to that benefit. Watching a whole marketing page is noisy, so a record can now name the exact sentence it relies on: Source Watch tracks only that sentence and downgrades the option to "check it first" if the sentence disappears.

## How it's built

```
 browser
    │
 CloudFront ── security headers (CSP, HSTS, frame-deny)
    ├── /        → S3 site bucket (private, Origin Access Control)
    └── /api/*   → API Gateway HTTP API (10 rps, burst 20)
                      │
                   Lambda: FastAPI (Python 3.13, arm64)
                      ├── deterministic engine  ← backend/knowledge/*.json
                      ├── Amazon Textract AnalyzeExpense  (receipt, optional)
                      ├── Amazon Bedrock, Nova 2 Lite     (fault photo, optional)
                      └── DynamoDB  (Source Watch status, daily AI-call cap)

 EventBridge Scheduler (06:00 UTC) → Lambda: Source Watch
                      ├── fetch Apple index + every source page, hash visible text
                      ├── DynamoDB (status per source)
                      └── S3 (versioned snapshot whenever a page changes)

 AWS Budgets → email alert
```

| Piece | Choice | Why |
| --- | --- | --- |
| Front door | One **CloudFront** distribution: `/` to a private **S3** bucket (Origin Access Control), `/api/*` to the API | One origin, so no CORS and no API URL baked into the frontend. Security headers (CSP, HSTS, frame-deny) set by a response-headers policy |
| API | **API Gateway HTTP API** (throttled to 10 req/s, burst 20) to **Lambda** (Python 3.13, arm64) running FastAPI through Mangum | Zero idle cost. arm64 for Graviton's lower price per GB-second |
| Engine | Deterministic Python over JSON source records in `backend/knowledge/` | Every claim, condition and caveat traces to a record with a source URL and a human verification date |
| Receipt reading | **Amazon Textract** `AnalyzeExpense` | Pre-fills store, date and total. The confidence shown is Textract's own |
| Photo reading | **Amazon Bedrock** Converse API, Amazon Nova 2 Lite (vision) | Describes visible damage only. It never decides coverage |
| Source Watch | **EventBridge Scheduler** + Lambda + **DynamoDB** (status) + **S3** (versioned snapshots) | Daily, cheap, auditable |
| Spend guard | DynamoDB counter per UTC day, conditional update, **fails closed**; **AWS Budgets** alert | The upload endpoint is public and calls paid services |
| Infrastructure | One **AWS SAM** template | `scripts/deploy.sh` builds, deploys, uploads the site, runs Source Watch once and smoke-tests, logging to `docs/evidence/` |

### Where the AI is, and where it is not

- The model **reads** (receipt fields via Textract, a photo description via Bedrock). The user sees and corrects what it read before anything is evaluated.
- The model **never decides** coverage, dates, conditions or caveats. Those come from source records and deterministic date arithmetic.
- If Bedrock is unavailable, RemedyAI records "not analyzed" instead of inventing observations.
- Demo cases are marked **Sample data**. Nothing on screen claims to be a Textract or Bedrock result unless it is.

### Privacy

- RemedyAI stores nothing a user enters: no accounts, cookies, analytics or saved cases.
- Photos are optional. Before anything is uploaded the form asks the user to cover their name, address, card number and faces, and the upload button stays disabled until they tick a box. Photos are re-encoded in the browser, which removes GPS metadata, and are only sent when the user presses "Read photos".
- The site has a plain-language privacy section covering what is used, who processes it (AWS, US East), what is kept (nothing; error logs hold only error types for 14 days) and how the per-visitor limit works.
- Typing is always an option, and the form suggests products, stores, payment methods and fault descriptions as you type. The suggestions are bundled with the site, so nothing is sent while typing. Dates can be typed in common formats or picked from a calendar.
- **No sign-up, on purpose.** Accounts would mean storing names and emails for no benefit to a one-off check. Deadline reminders come from an "Add to my calendar" file built in the browser instead, so RemedyAI still stores nothing. Optional accounts only make sense later, for tracked claims.

## How the coding agent built and shipped it

The coding agent was **Kiro**, working in a terminal authenticated as a dedicated IAM user. It:

1. Audited the first version against the hackathon rules and found it would fail the ship gate (not deployed, broken packaging, a retired Bedrock model).
2. Researched each source live and rewrote the knowledge records to state only what each page says.
3. Built Source Watch, the upload flow, the spend guard and the single-origin SAM stack.
4. Chose the Bedrock model by listing what was active in the account and making a real Converse call, rather than picking from a list.
5. Built the Lambda package with arm64 wheels, deployed with SAM, uploaded the site and smoke-tested the live URL.

**Proof of the connection** is AWS's own record, not a screenshot of a chat:

- `aws sts get-caller-identity` from the agent's session, at the top of every deploy log in `docs/evidence/`.
- A **CloudTrail** export of every API call made with the agent's IAM user (`docs/evidence/cloudtrail-*.md`). From the first deploy through the export at 2026-09-30 17:16 UTC that was **1,311 events, 73 of them mutating, across 12 AWS services**, starting with the stack's `CreateChangeSet` at 2026-09-29 18:36:09Z. Every entry keeps AWS's own request ID, so any line can be checked against the account's event history.
- The live site's own `/api/sources` shows Source Watch runs with timestamps, triggered first by the agent's deploy script and then by the daily schedule.

## What went wrong (and what it changed)

1. **The first demo was built on a program Apple had quietly dropped.** The original headline case was the iPhone 12 no-sound program. Its page is still online, but it is no longer on Apple's service-program index, and nearly every affected phone is past its 3-year window. That is the reason Source Watch exists.
2. **Windows were measured against the wrong date.** The engine compared the failure date to the purchase date. A phone that failed inside the window in 2023 still showed as covered in 2026. Windows are now measured against the claim date, and a closed window becomes a note, never a match.
3. **The fallback invented evidence.** With no photo, an early version generated plausible visual observations ("front glass intact") from the product name. That contradicted the whole point of the product, so it was removed, and sample data is now labelled.
4. **The Bedrock model had reached end-of-life before the hackathon started.** The original template pinned Claude 3.5 Sonnet v1, which reached end-of-life on Bedrock on 2026-07-30. Every photo analysis would have silently failed. The model is now a stack parameter, checked with a live call.
5. **Three Visa figures had no source.** Claim limits and a "60–90 day" reporting window were in the knowledge record but not on Visa's page. They were removed.
6. **A reviewer entered a US receipt as a UK claim, and RemedyAI accepted it.** The dates were right, but the result didn't show the failure date, so the reviewer couldn't check them, and nothing compared the receipt with the country chosen. Every result now shows a timeline (purchase, failure, claim date, deadline). A currency on the receipt that doesn't fit the chosen country is now a hard check: the consumer-law option is held and no claim PDF is produced until the user confirms. A different receipt date or store is shown as a warning.
7. **Scotland got the wrong deadline.** Every UK case used 6 years. The form now asks which part of the UK: England and Wales and Northern Ireland use 6 years, Scotland 5.
8. **A security review found two real flaws in the claim PDF.** Text typed into the form was read as PDF markup, so an image tag could make the server load a file into the PDF and a link tag could plant a link in a RemedyAI-branded document. And the PDF endpoint trusted the result the browser sent, so a PDF could claim coverage the engine never found. All PDF text is now escaped, and the server re-evaluates the case itself before building any PDF. Both have regression tests.

## What it doesn't know

| Unknown | Why |
| --- | --- |
| Whether your iPhone 14 Plus serial is in Apple's affected range | Only Apple's serial checker knows. RemedyAI sends you there |
| Your device's first retail sale date | If it was bought used or refurbished, the 3-year window may have started before your purchase |
| Your card issuer's exact terms | Visa's page defers to the issuer's Guide to Benefits |
| Every program that exists | Six verified routes today. Adding one means verifying its source by hand first. Source Watch flags Apple programs that have no record yet |
| Whether a changed page changed the terms | Source Watch detects that text changed, not what the change means. A person re-verifies |

## Cost

- **Idle cost is close to zero.** Lambda, HTTP API, DynamoDB on-demand, S3, CloudFront and one daily scheduled run are all billed per use.
- **The paid part is the optional photo reading.** Textract `AnalyzeExpense` is $0.01 per page ([pricing](https://aws.amazon.com/textract/pricing/)). One Bedrock call on Nova 2 Lite used a few hundred tokens in our tests.
- **The ceiling is enforced, not hoped for.** At most 100 photo reads per UTC day (about $1/day in the worst case), and at most 10 per visitor so one person can't use up the day. Both are counted in DynamoDB with conditional writes that refuse the call if a counter cannot be read. Visitors are counted by an HMAC of their IP with a random key that changes daily and expires after 2 days; raw IPs are never stored. API Gateway throttles at 10 requests/second. An AWS Budgets alert fires at 50% of $10/month.
- Checking a case without photos calls no paid AI service at all.

## Where it goes next (Startups lane)

- **First users:** people whose warranty just ended (device forums, repair shops that see these faults daily).
- **Corpus growth:** each new route is a JSON record plus a Source Watch entry, verified by a person before it goes live. The home page lists what is covered today (built from the same records the engine uses) and what is planned: new Apple programs as they appear, Samsung and Google programs, Mastercard and American Express benefits, the EU 2-year guarantee, and consumer law in more countries.
- **Business model:** free checks; paid tracked claims (deadline reminders, follow-up letters). Repair shops and card issuers are the partner channel: both benefit when a covered repair is claimed instead of paid out of pocket.
