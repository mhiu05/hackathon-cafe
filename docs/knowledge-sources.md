# Knowledge Sources & Data Provenance — Biblio 79 Ngụy Như Kon Tum

Status as of **2026-11-14**. Generated artifacts: `data/knowledge/normalized/*`, `data/knowledge/knowledge_extended.md`,
`data/knowledge/ingestion_report.md` (measured results). This document explains *how* they were produced and the rules
the app must keep.

## 1. Target branch identity

| Field | Value | Evidence |
|---|---|---|
| `branch_id` | `biblio-79-nguy-nhu-kon-tum` | — |
| Names | "BIBLIO CAFE SÁCH" (menu), logo "BIBLIO BOOKS COFFEE", "Biblio Book Cafe - 79 Ngụy Như Kon Tum" (Google Maps), "Biblio - Cafe Sách Ngụy Như Kon Tum" (Facebook) | photos, Maps, Book365, Tadiha |
| Address | 79 Ngụy Như Kon Tum, Làng sinh viên Hacinco, Thanh Xuân, Hà Nội | service-board photo, Google Maps, TikTok @bibliocafesach, MIA 08/2026, 1000 Libraries 06/2026 |
| Coordinates | 21.0013374, 105.8029646 — Plus code 2R23+G5 | Google Maps |
| Phone | **0976 214 224** | service-board photo + TikTok @bibliocafesach (06/2026) |
| Hours | **07:00–22:30 daily** | drink-menu photo, TikTok, MIA, Book365, 1000 Libraries |
| Facebook | facebook.com/Khonggianvanhoadongtay ("Biblio - Cafe Sách Ngụy Như Kon Tum") — content not retrievable (login wall) | Book365, Tadiha |
| TikTok | @bibliocafesach (self-identifies address/phone; not staff-confirmed) | Apify TikTok run |
| Website | none found | — |
| Google Maps snapshot | 4.4/5, 178 reviews (2026-11-14) | Apify Google Maps run |

**Conflicts kept, not resolved silently** (`doc-location-conflicts`): hotline 024 2215 7878 and hours 07:00–23:00 (Tadiha 2022);
"Cổng 1 - 79"; Traveloka's "Cafe sách Đông Tây, 99 Ngụy Như Kon Tum"; "79a" (TikTok/Civilis); rating 4.0 (Book365, undated).
Rule: in-store photos and 2026 branch sources win over older third-party articles.

## 2. Verification vocabulary

| `verification_status` | Meaning | Indexed for RAG? |
|---|---|---|
| `owner_verified` | Confirmed by café staff/owner. **No record has this status yet.** Never set for web data. | yes |
| `verified_branch` | Source explicitly identifies 79 Ngụy Như Kon Tum (photo at the branch, branch listing, article naming the branch, branch's own account) | yes |
| `brand_general` | About the Biblio chain, not a specific branch | yes (agent must phrase as chain-level) |
| `conflicting` | Contradicts another source; kept to explain the conflict | yes (as the conflicts document) |
| `unverified_branch` | Plausibly this branch but not identifiable → **pending verification** | **no** |
| `rejected` | Another branch (70 Tam Khương, Chùa Bộc…) or another business | **no** |

`content_kind`: `fact`, `review` (customer opinion — never stated as fact), `inference`, `event`, `product`, `service`.
Menu `suggested_tags` are **inferred from item names only** and are stored apart from facts.

## 3. Sources

| Source id | Type | Status | Used for |
|---|---|---|---|
| `src-photo-drink-menu`, `src-photo-food-menu`, `src-photo-service-board` | in-store photos (user-provided bundle) | verified_branch | menu, prices, hours, phone, co-working, rooms |
| `src-user-bundle` | `biblio_cafe_kb_bundle/*` (read-only originals) | verified_branch | transcription notes |
| `src-gmaps-listing`, `src-gmaps-reviews` | Apify `compass/crawler-google-places` | verified_branch | location, attributes, rating, 29 reviews |
| `src-tiktok-bibliocafesach` | Apify `clockworks/tiktok-scraper` | verified_branch | 3 captions (identity, working space, rooms) |
| `src-web-mia-2026` | MIA.vn 20/08/2026 | verified_branch | address, hours, description |
| `src-web-1000libraries-2026` | 1000 Libraries 15/06/2026 | verified_branch | lending library, seating, workshops/rental |
| `src-web-book365` | Book365 (undated) | verified_branch | >1000 m², kids area, cultural events |
| `src-web-tadiha-2022` | Tadiha 03/11/2022 | verified_branch (stale) | kids area, library card (unverified now), branch list |
| `src-web-toplist` | Toplist (undated) | brand_general | chain description, Thanh Xuân largest |
| `src-web-traveloka` | Traveloka | conflicting | "Cafe sách Đông Tây, 99 Ngụy Như Kon Tum" |
| `src-web-tatinta-4357`, `src-web-thesmartlocal` | articles about 70 Tam Khương | rejected | branch disambiguation only |
| `src-web-wanderlog` | Chùa Bộc listing (permanently closed) | rejected | branch disambiguation only |
| `src-facebook-page`, `src-web-restaurantguru`, `src-web-topcv`, `src-web-maptons` | not retrievable (login/403/503/connection) | — | identity cross-check only; no content used |
| `src-kb-curation` | synthesis documents with `citations` | verified_branch | FAQ: study/work, parking, kids, events/rental, room booking, unverified info, conflicts, branches |

## 4. Collection pipeline (reproducible)

```
External data ──collect.py──▶ data/knowledge/raw/ (gitignored)
             ──curation────▶ data/knowledge/curated/*.json (hand decisions + citations, committed)
             ──normalize.py▶ data/knowledge/normalized/* (committed) + knowledge_extended.md
             ──ingest.py───▶ data/cafe.db  (catalog tables + kb_* + Voyage vectors; cache in data/knowledge/embeddings/)
             ──verify.py───▶ data/knowledge/ingestion_report.md + eval/kb_eval_results.json
```

Apify is **never** called at request time (`ENABLE_APIFY_LIVE_SEARCH=false`). Runtime path:
cached knowledge → Voyage query embedding → NumPy cosine → agent. Prices, availability and order status come from SQL only.

### Apify cost control (measured)

| Actor | Input bounds | Hard cap (`max_total_charge_usd`) | Actual `usage_total_usd` | Run id |
|---|---|---|---|---|
| `compass/crawler-google-places` | startUrls = the branch URL, 1 place, `maxReviews=30`, `scrapeReviewsPersonalData=false`, images/Q&A/contacts/leads/competitors off | 0.50 | **0.0212** | `hTvPCbgInf1lsw9ig` |
| `clockworks/tiktok-scraper` | 2 search queries × 10, `max_items=20`, downloads/subtitles/comments/AI summaries off | 0.50 | **0.0750** | `qbedrS1CtnuG11vmc` |

Apify rejects caps below $0.50 per run, so the two caps sum to the $1.00 budget; real spend was **$0.0962**.
`collect.py` refuses to start a second run when `raw/apify/<name>/run_meta.json` exists (use `--from-run <id>` to re-download)
and never retries failed runs.

### Branch-identity rules applied

1. Accept when the source names 79 Ngụy Như Kon Tum / "Biblio … Ngụy Như Kon Tum" / "Biblio Book Cafe (in Thanh Xuân)", or is the branch's own listing/account.
2. Reject when the source names another address (70 Tam Khương, Chùa Bộc, Xa La, Quang Trung) or another business on the same street.
3. Pending (`unverified_branch`) when the venue is not named (generic TikTok clips, "79a").
4. Old data (2022) stays but is labelled stale; newer in-store/branch sources win.

## 5. Results (from `ingestion_report.md`)

- Menu: 51 items / 9 categories / 4 variants (menu_001 Nâu|Đen, menu_023 1|2 người); all `availability=unknown`, `price_verified=false`.
- Services: 3 co-working packages, 5 rentable spaces, 22 service facts.
- Documents: 57 normalized (54 indexed, 3 rejected) → 56 chunks, 56 Voyage vectors (`voyage-4-lite`, 512-d, float32, L2-normalised).
- TikTok: 20 collected → 3 accepted, 6 pending, 11 rejected. Google Maps reviews: 30 collected, 1 off-topic excluded, no personal data.
- Retrieval eval (30 questions, 29 with retrieval): vector hit@5 29/29 (one bait question correctly returns nothing), hit@1 21/29, MRR 0.806;
  keyword fallback hit@5 27/29; SQL fact checks 8/8. First run before fixes: 26/29 — see §6.
- Negative controls (unrelated / prompt-injection queries) top cosine ≈ 0.285 < `DEFAULT_MIN_SCORE` 0.30 → empty result.

## 6. Honest notes on the evaluation

After the first run (26/29) three changes were made and the eval re-run: (1) retrieval now keeps one chunk per document
(diversity); (2) a focused FAQ `doc-faq-room-booking` was added because the "no availability" statement was buried in a long
document; (3) expectations were widened for q14 (`doc-photo-menu-overview` carries the sweetness caveat) and q28 accepts an
empty result (no source mentions a 50% student discount, so "no evidence" is the correct retrieval outcome). The eval set is
small and authored by the same person who built the corpus — treat it as a regression suite, not a benchmark.

## 7. Missing / to confirm with staff before the demo

See `data/knowledge/normalized/unverified_claims.json` (21 items). Highest impact for the demo:
1. Which items are available today (staff can set this in Admin → Menu; seed is `unknown` for all).
2. Whether listed prices are current; meaning of the handwritten X next to "Trà xoài Yakult".
3. Ordering rules: pay at counter, table numbers or name pickup.
4. Any upcoming event to show (none verified).
5. Owner sign-off to flip specific facts to `owner_verified` (edit `curated/*.json`, re-run normalize → ingest → verify).
