# Field test: real cases from public posts

16 people described a broken product in a public forum or a newspaper consumer column. Each case was
entered using only what the poster said, and run through the same engine as the live site, with the
claim date set to the day of the post. Inputs, sources and the exclusion list: [`cases.json`](cases.json).
Reproduce with `python scripts/field_test.py`.

How the cases were chosen: searches for broken-device posts on Apple Community, Samsung Community, Sky
News's Money Problem column and the MoneySavingExpert forum, taken in search order. A post was skipped
only if it gave no purchase date or did not load (11 skipped, listed in `cases.json`).
Where a poster gave a month or 'about N months', the date is approximate. A country the poster didn't
state was entered as 'other', so it can't create a match.

## Result

- **Route found:** 6 of 16
- **Route found, confirm details first:** 0 of 16
- **No covered route:** 10 of 16

Before and after: the first run (2026-10-01) found a route for 4 of 16. The biggest gap was Samsung, so the next record verified and added was Samsung's U.S. phone warranty; with it, 6 of 16.

Why nothing matched:

- the poster didn't say where it was bought, and it wouldn't match as a U.S. purchase either: 4
- would match if bought in the U.S.; the poster didn't say where it was bought, and Apple's warranty there isn't covered yet: 2
- bought in Australia: Apple's warranty and consumer law there aren't covered yet: 1
- bought in India: Samsung's warranty and consumer law there aren't covered yet: 1
- would match if bought in the U.S.; bought in India, and Samsung's warranty there isn't covered yet: 1
- bought in the U.S.: no record covers this product at this age yet: 1

Sensitivity: 6 posts didn't say where the product was bought. Entered as U.S. purchases, 2 of them would get a route. The result above does not count them.

## Cases

| # | Product | Bought in | Posted | Outcome | Route or gap | Source |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | Apple iPhone 16 Pro | other / not stated | 2026-02-22 | No covered route | the poster didn't say where it was bought, and it wouldn't match as a U.S. purchase either | [post](https://discussions.apple.com/thread/256250464) |
| A2 | Apple iPhone 17 Pro Max | other / not stated | 2026-05-25 | No covered route | would match if bought in the U.S.; the poster didn't say where it was bought, and Apple's warranty there isn't covered yet | [post](https://discussions.apple.com/thread/256302831) |
| A3 | Apple iPad Pro M4 | other / not stated | 2026-03-01 | No covered route | the poster didn't say where it was bought, and it wouldn't match as a U.S. purchase either | [post](https://discussions.apple.com/thread/256254491) |
| A4 | Apple iPad (10th generation) | other / not stated | 2026-07-26 | No covered route | the poster didn't say where it was bought, and it wouldn't match as a U.S. purchase either | [post](https://discussions.apple.com/thread/256331802) |
| A5 | Apple AirPods Max | Australia | 2026-01-09 | No covered route | bought in Australia: Apple's warranty and consumer law there aren't covered yet | [post](https://discussions.apple.com/thread/256222932) |
| A6 | Apple Watch Series 12 | other / not stated | 2026-09-19 | No covered route | the poster didn't say where it was bought, and it wouldn't match as a U.S. purchase either | [post](https://discussions.apple.com/thread/256360354) |
| A7 | Apple iPad Air 11-inch | other / not stated | 2025-06-16 | No covered route | would match if bought in the U.S.; the poster didn't say where it was bought, and Apple's warranty there isn't covered yet | [post](https://discussions.apple.com/thread/256081662) |
| S1 | Samsung Galaxy Z Fold 7 | U.S. | 2026-07-29 | Route found | Samsung Care: 12-month built-in limited warranty for Galaxy phones (U.S.) (potentially eligible, deadline 2027-03-29) | [post](https://us.community.samsung.com/t5/Galaxy-Z-Series/Galaxy-ZFold-7-Warranty-issues/td-p/3629970) |
| S2 | Samsung Galaxy S23 | India | 2026-05-31 | No covered route | bought in India: Samsung's warranty and consumer law there aren't covered yet | [post](https://r2.community.samsung.com/t5/Galaxy-S/Samsung-s-Pink-Line-Scam-Warranty-Ends-Customer-Pays/td-p/22217370) |
| S3 | Samsung Galaxy S24 | India | 2026-06-25 | No covered route | would match if bought in the U.S.; bought in India, and Samsung's warranty there isn't covered yet | [post](https://r2.community.samsung.com/t5/Galaxy-S/Samsung-Galaxy-S24-Display-Issue-Need-Official-Clarification/td-p/22407843) |
| S4 | Samsung washer/dryer combo | U.S. | 2026-07-31 | No covered route | bought in the U.S.: no record covers this product at this age yet | [post](https://us.community.samsung.com/t5/Laundry/Ongoing-Issue-with-a-Samsung-Washer-Dryer-Combo-Purchased-July/td-p/3631605) |
| S5 | Samsung Galaxy Z Fold | U.S. | 2026-05-12 | Route found | Samsung Care: 12-month built-in limited warranty for Galaxy phones (U.S.) (potentially eligible, deadline 2026-10-12) | [post](https://eu.community.samsung.com/t5/galaxy-s26-series/samsung-warranty-denied/td-p/14679303) |
| U1 | Samsung OLED TV | UK | 2025-09-30 | Route found | UK consumer rights on faulty goods (GOV.UK: Accepting returns and giving refunds) (potentially eligible, deadline 2029-11-15) | [post](https://news.sky.com/story/money-problem-my-1-2k-samsung-tv-broke-within-two-years-but-they-wont-give-me-any-money-back-13437866) |
| U2 | Refurbished smartphone | UK | 2025-11-17 | Route found | UK consumer rights on faulty goods (GOV.UK: Accepting returns and giving refunds) (potentially eligible, deadline 2030-07-15) | [post](https://news.sky.com/story/my-phone-has-broken-back-market-is-fobbing-me-off-what-are-my-rights-13470179) |
| U3 | Grundig washer dryer | UK | 2026-02-03 | Route found | UK consumer rights on faulty goods (GOV.UK: Accepting returns and giving refunds) (potentially eligible, deadline 2029-10-15) | [post](https://news.sky.com/story/money-problem-my-washing-machine-has-eaten-1-000-of-clothes-13499582) |
| U4 | Bluetooth speaker | UK | 2026-09-26 | Route found | UK consumer rights on faulty goods (GOV.UK: Accepting returns and giving refunds) (potentially eligible, deadline 2032-09-10) | [post](https://forums.moneysavingexpert.com/discussion/6684559/return-of-faulty-speaker) |

A route is what RemedyAI would tell the person to try first; the maker, card issuer or store makes the final decision.
