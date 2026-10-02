# RemedyAI: find the free repair you may still be owed after your warranty ends

**Live:** https://d1fnfajqesgvsl.cloudfront.net (no sign-up) · **Code:** https://github.com/Extraordinarytechy/remedy-ai

## The problem, in one real example

Apple runs a free repair program for iPhone 14 Plus rear cameras that show no preview. It covers units made between April 10, 2023 and April 28, 2024, for **three years from first retail sale**, and Apple says people who already paid for that repair can ask for a refund ([Apple](https://support.apple.com/iphone-14-plus-service-program-for-rear-camera-issue)). The standard warranty on the same phone is one year.

So an owner whose camera fails at month 30 is out of warranty but may still qualify for a free repair (Apple confirms by serial number and inspection), and nothing tells them. The windows for the earliest affected units have started closing: a phone first sold in April 2023 lost its free repair in April 2026. The last ones close around mid-2027.

That gap is not specific to Apple. Some credit cards add a year to the manufacturer warranty. In the UK, a buyer has up to 6 years (5 in Scotland) to claim a repair or replacement from the retailer for a faulty product. Each route has its own rules, dates and caveats, and each lives on a different page.

## What RemedyAI does

You describe what broke (optionally with a receipt photo and a photo of the fault). RemedyAI checks it against the **published source** for each route it knows about and returns, for every match:

- **why it matched**, with the dates it measured (the claim date, not just the failure date)
- **what you will need**, taken from the source
- **what could stop it**, also from the source (for Apple: a cracked back must be fixed first and may cost money)
- a **timeline**: purchase, failure and claim dates, and the deadline for each option
- a **claim PDF** and a draft letter

If a receipt photo was read, RemedyAI also **checks it against what you typed**. A receipt priced in dollars for a claim entered as a UK purchase holds the UK option and the claim PDF until you confirm where you bought it. A different receipt date also holds the claim PDF until you confirm it; a different store is shown as a warning.

If no source covers the case, it says so: `NO VERIFIED COVERAGE FOUND`, plus the sources it checked that did not apply and why. The answer lists, in plain words, why nothing matched for each kind of option (the maker's warranty ended on a given date, no repair program covers this model and fault, the card benefit is for Visa Infinite in the U.S. only, consumer law is for UK stores only). Each reason comes from the same records the engine uses.

Dates that can't be right are refused before anything is checked: a purchase more than 30 years before the claim date, or before the model went on sale. "iPhone 17 bought in January 2021" gets "The iPhone 17 went on sale in September 2025, so it can't have been bought in January 2021." The on-sale dates come from the makers' own announcements and are kept in `backend/data/`, apart from the coverage records. A phone with no date of its own is held to the date its family began: the first iPhone went on sale in June 2007, the first Pixel phone in October 2016 and the first Galaxy S in June 2010. Other products are never blocked by a date. Refused dates never get a claim PDF.

Twelve routes today (one of them an ended program kept to show delisting), from four kinds of source:

| Route | Source | Status in RemedyAI |
| --- | --- | --- |
| Apple One (1) Year Limited Warranty (U.S.; iPhone, iPad and other iOS devices) | Apple | Covers new launches such as iPhone 18 Pro (on sale September 18, 2026): defects for one year from purchase, claimed during the year. Accidental damage is not covered |
| Apple One (1) Year Limited Warranty (U.S.; Mac) | Apple | MacBook Air, MacBook Pro, iMac, Mac mini, Mac Studio and Mac Pro, one year from purchase. A JSON record only |
| Apple One (1) Year Limited Warranty (U.S.; Apple Watch) | Apple | One year from purchase; Apple Watch Edition has its own document and is not included |
| Apple One (1) Year Limited Warranty, Accessory (U.S.; AirPods, AirTag and Apple accessories) | Apple | The document Apple lists for AirPods, AirTag and accessories in the U.S. "Apple Pencil" and "MagSafe Charger" match; "AirPods case" does not, because it may be a third-party cover |
| Mac mini (2023, M2) no-power program | Apple | Active, on Apple's index since June 2025; serial check required. Found missing on 2026-09-30, verified against Apple's page and added |
| iPhone 14 Plus rear camera program | Apple | Active; requires Apple's serial check, so RemedyAI never says "eligible", only "possible: check your serial number" |
| iPhone 12 / 12 Pro no-sound program | Apple | Page still online, **not on Apple's index**; nearly every unit is past its window |
| Google Consumer Hardware Limited Warranty (U.S. and Canada; Pixel devices) | Google | One year from purchase (90 days if refurbished). Added as a JSON record only, with no Google-specific code |
| Pixel 9 Pro & 9 Pro XL Extended Repair Program | Google | Vertical display line (or flicker on 9 Pro), free display for 3 years from purchase; inspection first |
| Samsung Care 12-month built-in limited warranty (U.S.; Galaxy phones) | Samsung | Added after the field test showed Samsung as the biggest gap; a JSON record only. Terms from Samsung's Standard Limited Warranty |
| Visa Infinite extended warranty (+1 year on warranties of 3 years or less) | Visa | Issuer's Guide to Benefits governs; RemedyAI shows only what Visa's page states |
| UK consumer rights on faulty goods (6 years, 5 in Scotland) | GOV.UK | Includes the burden-of-proof shift after 6 months |

## What makes it different: Source Watch

A static warranty database goes stale quietly. I found this out the hard way (see "What went wrong"), so RemedyAI now checks its own sources every day:

- **EventBridge Scheduler** runs a Lambda at 06:00 UTC.
- It fetches every source page plus Apple's [service-program index](https://support.apple.com/service-programs), hashes the visible text, and **stores a dated snapshot in S3 whenever a page changes**.
- It records, per source: HTTP status, whether an Apple program is still listed on the index, when the text last changed, and which programs appeared or disappeared from the index since the previous run.
- The API reads that status on every evaluation. A route is **downgraded to "Source changed: re-verify first"** instead of being shown as a match if its page is unreachable, the sentence it relies on is gone, its text changed after it was last verified, its Apple program has left the index, or Apple's index can't be read. Downgraded routes are never used in the claim PDF or letter.
- Each run publishes a `DegradedSources` CloudWatch metric (embedded metric format, no extra API call). An alarm emails the owner when it is above zero; two more alarms cover a failed run and a missed run. If the newest check is more than 36 hours old, every route is treated as unverified.

The Source Watch table is on the home page, so anyone can see when each source was last verified and when it was last checked automatically.

It also compares Apple's list with the corpus and publishes a **gap alert**: any repair program Apple lists that RemedyAI has no record for. That check was added after the Mac mini (2023) no-power program turned up on Apple's list with no RemedyAI record (it had been listed since June 2025). Its page was verified and the record added on 2026-09-30, and the check now catches the next one automatically.

It has already done its job, and taught a lesson. On 2026-09-30 it recorded that the text of Visa's Visa Infinite page had changed since it was last verified. The page was re-read: the Extended Warranty wording (one extra year on eligible warranties of 3 years or less) was unchanged, so the record's verification date was updated. The page then changed again the same day, for reasons unrelated to that benefit. Watching a whole marketing page is noisy, so a record can now name the exact sentence it relies on: Source Watch tracks only that sentence and downgrades the option to "check it first" if the sentence disappears.

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

- RemedyAI doesn't save what a user enters or uploads: no accounts, cookies, tracking or saved cases. It keeps only anonymous totals of checks, checks with an option and claim PDFs, and a short-lived per-visitor code for the daily limits.
- Photos are optional. Before anything is uploaded the form asks the user to cover their name, address, card number and faces, and the upload button stays disabled until they tick a box. Photos are re-encoded in the browser, which removes GPS metadata, and are only sent when the user presses "Read photos".
- The site has a plain-language privacy section covering what is used, who processes it (AWS, in the United States), what is kept (error types and anonymous totals for 14 days; the per-visitor code for a few days) and how the per-visitor limit works.
- Typing is always an option, and the form suggests products, stores, payment methods and fault descriptions as you type. The suggestions are bundled with the site, so nothing is sent while typing. Dates can be typed in common formats or picked from a calendar.
- **No sign-up, on purpose.** Accounts would mean storing names and emails for no benefit to a one-off check. Deadline reminders come from an "Add to my calendar" file built in the browser instead, so RemedyAI still keeps no personal details. Optional accounts only make sense later, for tracked claims.

## How the coding agent built and shipped it

The coding agent was **Kiro**, working in a terminal authenticated as a dedicated IAM user. It:

1. Tested its early build end to end before the first deploy and fixed what would have stopped it shipping: a broken Lambda package and a retired Bedrock model.
2. Researched each source live and rewrote the knowledge records to state only what each page says.
3. Built Source Watch, the upload flow, the spend guard and the single-origin SAM stack.
4. Chose the Bedrock model by listing what was active in the account and making a real Converse call, rather than picking from a list.
5. Built the Lambda package with arm64 wheels, deployed with SAM, uploaded the site and smoke-tested the live URL.

**Proof of the connection** is AWS's own record, not a screenshot of a chat:

- `aws sts get-caller-identity` from the agent's session, at the top of every deploy log in `docs/evidence/`.
- A **CloudTrail** export of every API call made with the agent's IAM user (`docs/evidence/cloudtrail-*.md`). From the agent's first call (2026-09-29 18:10 UTC) through the export at 2026-10-01 20:14 UTC that was **4,809 events, 168 of them mutating, across 15 AWS services**; the first change was the stack's `CreateChangeSet` at 2026-09-29 18:36:09Z. Since the 2026-10-01 18:05 UTC deploy, calls also carry the client-set `app/kiro-ide` user-agent tag (165 in that export). Every entry keeps AWS's own request ID, so any line can be checked against the account's event history.
- The live site's own `/api/sources` shows Source Watch runs with timestamps, triggered first by the agent's deploy script and then by the daily schedule.

## What went wrong (and what it changed)

1. **The first demo was built on a program Apple had quietly dropped.** The original headline case was the iPhone 12 no-sound program. Its page is still online, but it is no longer on Apple's service-program index, and nearly every affected phone is past its 3-year window. That is the reason Source Watch exists.
2. **Windows were measured against the wrong date.** The engine compared the failure date to the purchase date. A phone that failed inside the window in 2023 still showed as covered in 2026. Windows are now measured against the claim date, and a closed window becomes a note, never a match.
3. **The fallback invented evidence.** With no photo, an early version generated plausible visual observations ("front glass intact") from the product name. That contradicted the whole point of the product, so it was removed, and sample data is now labelled.
4. **The Bedrock model had already reached end-of-life.** The original template pinned Claude 3.5 Sonnet v1, which reached end-of-life on Bedrock on 2026-07-30. Every photo analysis would have silently failed. The model is now a stack parameter, checked with a live call.
5. **Three Visa figures had no source.** Claim limits and a "60–90 day" reporting window were in the knowledge record but not on Visa's page. They were removed.
6. **A tester entered a US receipt as a UK claim, and RemedyAI accepted it.** The dates were right, but the result didn't show the failure date, so the tester couldn't check them, and nothing compared the receipt with the country chosen. Every result now shows a timeline (purchase, failure, claim date, deadline). A currency on the receipt that doesn't fit the chosen country is now a hard check: the consumer-law option is held and no claim PDF is produced until the user confirms. A different receipt date now holds the claim PDF the same way; a different store is shown as a warning.
7. **Scotland got the wrong deadline.** Every UK case used 6 years. The form now asks which part of the UK: England and Wales and Northern Ireland use 6 years, Scotland 5.
8. **A security review found two real flaws in the claim PDF.** Text typed into the form was read as PDF markup, so an image tag could make the server load a file into the PDF and a link tag could plant a link in a RemedyAI-branded document. And the PDF endpoint trusted the result the browser sent, so a PDF could claim coverage the engine never found. All PDF text is now escaped, and the server re-evaluates the case itself before building any PDF. Both have regression tests.
9. **A pre-launch security check found a way around CloudFront.** The API Gateway URL was still public, and the API trusted the `CloudFront-Viewer-Address` header to count visitors. Anyone calling that URL directly could set the header themselves and get a fresh per-visitor allowance each time (the daily total still held). CloudFront now adds a random secret header, and the API refuses any request without it. It also only trusts the visitor address when that header is present.
10. **A full code read-through before launch found the engine applying its own rules unevenly.** The Visa route compared the failure date with the purchase date but never with the claim date, so a benefit that ended in 2023 could still show as an option, and it matched purchases outside the U.S. A program the record itself marked as delisted could read "likely" whenever the daily source check hadn't run. "iPhone 18 Pro case" matched Apple's hardware warranty. And the claim date, which every deadline is measured against, could be set by the caller. All are fixed with tests: every route now checks the claim date and its country, delisted or unverified options are never used in the claim letter, accessories don't match devices, and the server sets the claim date. The same pass added byte-level checks on receipt uploads, length limits on every nested field, a daily cap on claim PDFs, item-level DynamoDB permissions, and a review step that shows what was read from photos before it is used.
11. **A second code review found three places that failed open.** The photo reader's reply was coerced with Python's `bool()`, so the text `"false"` counted as true. A source page edited after it was verified only added a warning, so the route stayed usable in the claim PDF. And when Apple's index couldn't be read, the delisting check returned "unknown" and the route stayed live, with no alarm. Now the reply must match a strict schema or it is discarded, any change after verification and an unreadable index both mean "check it first", and a `DegradedSources` alarm emails the owner. Each has regression tests.

## What it doesn't know

| Unknown | Why |
| --- | --- |
| Whether your iPhone 14 Plus serial is in Apple's affected range | Only Apple's serial checker knows. RemedyAI sends you there |
| Your device's first retail sale date | If it was bought used or refurbished, the 3-year window may have started before your purchase |
| Your card issuer's exact terms | Visa's page defers to the issuer's Guide to Benefits |
| Every program that exists | Twelve verified routes today. Adding one means verifying its official page first. Source Watch flags Apple programs that have no record yet |
| Whether a changed page changed the terms | Source Watch detects that text changed, not what the change means. The page is then re-verified |

## Cost

- **Idle cost is close to zero.** Lambda, HTTP API, DynamoDB on-demand, S3, CloudFront and one daily scheduled run are all billed per use.
- **The paid part is the optional photo reading.** Textract `AnalyzeExpense` is $0.01 per page ([pricing](https://aws.amazon.com/textract/pricing/)). One Bedrock call on Nova 2 Lite used a few hundred tokens in testing.
- **The ceiling is enforced, not hoped for.** At most 40 photo reads per UTC day (well under $1/day in the worst case), and at most 10 per visitor so one person can't use up the day. Both are counted in DynamoDB with conditional writes that refuse the call if a counter cannot be read. Visitors are counted by an HMAC of their IP with a random key that changes daily and expires 2 days after last use; raw IPs are never stored. Claim PDFs, which use no paid AI service, are capped the same way (30 per visitor, 2,000 per day). API Gateway throttles at 10 requests/second. An AWS Budgets alert fires at 50% of $10/month.
- Checking a case without photos calls no paid AI service at all.

## Where it goes next

- **Field test:** 16 broken-product cases from public posts were run through the engine using only what each poster said ([results](field-test/results.md)). The first run found a route for 4, all through UK consumer law, and 5 of the 12 misses were Samsung devices. Samsung's U.S. phone warranty was then verified and added as a record, and the same 16 cases give 6 routes. The largest remaining gap is makers' warranties outside the U.S.
- **First users:** people whose warranty just ended (device forums, consumer columns, repair shops that see these faults daily).
- **Corpus growth:** every route is verified against its official page before it goes live, then watched by Source Watch. A new manufacturer warranty or repair program (any brand) is only a JSON record, because those evaluators are driven by the record's data. A new kind of route, such as another card network or another country's consumer law, also needs its own small evaluator today, as Visa Infinite and UK law do. The home page lists what is covered today (built from the same records the engine uses) and what is planned: new Apple programs as they appear, Samsung's repair programs and its warranties for tablets, watches and appliances, makers' warranties outside the U.S. (the biggest gap in the field test), Mastercard and American Express benefits, the EU 2-year guarantee, and consumer law in more countries.
- **Business model (planned):** free checks; paid tracked claims (deadline reminders, a follow-up letter if a claim is refused, escalation), priced per claim and well below the repair recovered. The natural partners are repairers the maker pays for warranty and repair-program work, such as Apple, Google and Samsung authorized service providers, since RemedyAI would send them customers whose repair is free to the customer. Complaint-letter tools such as Resolver and Which? help people write to a company; RemedyAI tells them which free route applies, until when, and keeps that answer checked against the source.
