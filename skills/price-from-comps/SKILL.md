---
name: price-from-comps
description: Use when the owner sends photos or a description of a card or collectible to list on eBay and needs a start price and Buy It Now from recent sold comps.
---
# Price from sold comps (browser)

eBay's sold-price API (Marketplace Insights) is restricted, so comps come from eBay's public Sold listings in the browser. NovaBay's MCP tools stay read-only and are not used for this.

## 1. Identify the item exactly
From the photos, write down: year, set, player/subject, card number, parallel/color, serial numbering (e.g. /250), autograph or relic, and grade + grader (PSA/BGS/SGC/raw). If any of these can't be read, ask the owner before pricing.

## 2. Pull sold comps in the browser
Open eBay sold-items search for the exact item, for example:
`https://www.ebay.com/sch/i.html?_nkw=<year+set+player+number+parallel+grade>&LH_Sold=1&LH_Complete=1&_sop=13`
- Keep only exact matches: same card, parallel, numbering and grade/grader.
- Use sales from the last 60–90 days; take 3–5 of them.
- Drop Best Offer outliers and lots. Note each sale's price (incl. shipping if listed), date and link.
- Optional cross-check: 130point or Card Ladder.
- If there are no exact matches, stop and ask the owner. Never guess from a different parallel or grade.
- If eBay blocks the browser (captcha loop or access denied), report it and stop; don't scrape around it.

## 3. Set the price (owner's default rules; the owner may override)
- Most recent sale $5–50: 7-day auction starting at $0.99, no Buy It Now.
- $50 and up: start 10% under the most recent sale. Buy It Now = the higher of the comps average or start price + 30%.
- Under $5, or non-card items: ask the owner first.

## 4. Report before listing
Show the owner: item identification, the comps used (price, date, link), the proposed format, start price and Buy It Now. Never list, revise or end anything without the owner's OK.
