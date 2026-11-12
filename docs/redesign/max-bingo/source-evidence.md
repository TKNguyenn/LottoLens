# Max 3D / Pro: primary-source evidence

Checked 2026-11-11. Research only; no product files changed, no installation or paid AI call. The PDF skill was used to render decisive scanned pages. Downloaded PDFs and rendered pages are local research artifacts, excluded from the public repository; retrieve official documents through the links below. `sources/sha256.json` records their byte counts and SHA-256 hashes.

## Draw mechanism: verified for both current products

The actual official introduction pages are [Max 3D](https://vietlott.vn/vi/choi/max3d/gioi-thieu-san-pham-max3d) and [Max 3D Pro](https://vietlott.vn/vi/choi/max3dpro/gioi-thieu-san-pham-max3dpro). Their July 2026 rules links were retrieved from the HTML, rather than guessed.

- [Max 3D draw rules, July 2026](https://media.vietlott.vn//main.vi/07.2026/cms/game/max3d.pdf), saved as `max3d-2026.pdf`: printed page 5, Article 7(2)(b), describes 20 triple draws. Each draw begins by releasing the previous winning balls back into the mixing chamber, followed by random mixing and selection. Visually checked `max3d-2026-05.png`.
- [Max 3D Pro draw rules, July 2026](https://media.vietlott.vn//main.vi/07.2026/cms/game/max3dpro.pdf), saved as `max3dpro-2026.pdf`: printed page 4, Article 6(2), assigns 8 draws to third prize, 6 to second, 4 to first, and 2 to special. Printed page 5, Article 7(2)(b), explicitly returns the winning balls before every subsequent draw. Printed page 7, Article 8(1)(c) and 8(2)(b), specifies three drums, three ball sets with ten balls numbered 0–9, and repeats the replacement process through all 20 results. These pages were rendered and visually checked.
- [Archived 2019 Max draw rules](https://media.vietlott.vn/vi/04.2019/system/archivedate/the-le-max-3d.pdf), saved as `the-le-max-3d.pdf`, independently agrees in Article 7(2)(b), printed page 4, and Article 8(1)(c), printed page 6. Its prize labels are older; use the current rules above for the product labels.

**Mathematical interpretation:** replacement is explicitly verified. The theoretical fair-draw model uses independent uniform digits from each drum, hence uniform independent triples from 000–999 between draws. Independence and perfect fairness are model assumptions consistent with this random-mixing/replacement process; this research does not claim an empirical guarantee about hardware.

## Pro winning events: verified text plus official demo corroboration

[Pro participation rules, August 2022](https://media.vietlott.vn//main.vi/08.2022/cms/game/max3dpro.pdf), saved as `max3dpro-2022.pdf`, remain linked from the current official introduction page. Printed pages 9–10, Article 8(2), give ordered special/reverse special, pairs within the 4/6/8 groups, pairs across all groups, and single matches in special/rest groups. Page 10 explicitly allows identical ticket pairs, doubles first-through-sixth prize amounts, combines special/reverse amounts for an identical pair, and adds multiple prizes. The table does not say “exactly one” or prescribe an exclusion when two values match. These pages were rendered and visually checked.

The [official Pro how-to page](https://vietlott.vn/vi/choi/max3dpro/cach-choi) embeds [Vietlott's own demo](https://vietlott.vn/game/max3dpro). Its [Result.js](https://vietlott.vn/game/max3dpro/js/Result.js), saved as `max3dpro-demo-Result.js`, corroborates the ambiguous edge cases:

| Function and saved-file line | Event observed in official source |
| --- | --- |
| `getPrize3D3D_GiaiDacBiet`, 1200 | Exact ordered ticket pair against the two special results. |
| `getPrize3D3D_GiaiPhuDacBiet`, 1217 | Reverse ordered ticket pair. |
| `getPrize3D3D_GiaiNhat`, 1235; `GiaiNhi`, 1267; `GiaiBa`, 1297; `GiaiTu`, 1326 | Two flags require two distinct result positions; an identical ticket A,A therefore requires at least two A occurrences. Extra repeated results do not disqualify the pair. |
| `getPrize3D3D_GiaiNam`, 1358 | Each special result is independently compared with both ticket values; any match qualifies, including when both values match. |
| `getPrize3D3D_GiaiSau`, 1404 | The same inclusive check across the remaining 18 results. |

These are source-code observations, not a claim that the web demo was exercised in a browser. The formal rules are controlling; demo code supplies corroboration of event predicates. Its identical-pair cash-count arithmetic appears to multiply more than once, so it must not be copied as authoritative payout logic.

**Implementation interpretation:** for distinct A,B, pair events require count(A) >= 1 and count(B) >= 1 in the relevant group; for identical A,A, count(A) >= 2. Single-match events require any A or B occurrence, regardless of pair prizes. Special and reverse events coincide for identical tickets. Marginal prize events overlap; calculate their union separately. This supports event probabilities, not an asserted count of payable repeated-result combinations.

The [SMS Max page](https://info.vietlott-sms.vn/hdsd/game_3d.html) and [SMS Pro page](https://info.vietlott-sms.vn/hdsd/game_3dp.html) were also read and saved as `game_3d.html` / `game_3dp.html`; their tables agree with these group sizes, ordering, identical-pair allowance, and additive prizes.

## Limits and reproduction

- Web browsing returned 403 for several Vietlott URLs. Python `requests` successfully downloaded the actual PDFs with HTTP 200 and `%PDF` signatures. `pdfinfo` identified the current PDFs as ten-page documents; `pdftoppm` rendered the cited pages. A 200 response alone was never treated as proof of content.
- Repeated-result payout multiplicity is not fully resolved by the formal prose. Do not display exact winnings or expected money from these predicates alone. The requested probability of receiving a given tier at least once is supported by the inclusive event interpretation and the official demo checks above.
- The PDFs are official published copies linked on the product pages at retrieval time. No claim is made about unannounced future changes or applicability of current amounts to historical draws.
