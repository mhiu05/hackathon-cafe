# Ingestion report — Biblio 79 Ngụy Như Kon Tum

> Sinh bởi `scripts/knowledge/verify.py`. Mọi số liệu dưới đây được đo khi chạy script, không ước lượng.

## Kết quả kiểm tra

| Check | Kết quả | Chi tiết |
|---|---|---|
| parse cafe_profile.json | PASS |  |
| parse menu.json | PASS |  |
| parse services.json | PASS |  |
| parse source_manifest.json | PASS |  |
| parse events.json | PASS |  |
| parse social_insights.json | PASS |  |
| parse unverified_claims.json | PASS |  |
| parse curated/external_knowledge.json | PASS |  |
| parse curated/synthesis_documents.json | PASS |  |
| parse documents.jsonl | PASS | 57 records |
| documents have required fields | PASS |  |
| documents use allowed status/kind enums | PASS |  |
| no web data marked owner_verified | PASS |  |
| ingestible documents belong to branch 79 NNKT or brand-general | PASS |  |
| 70 Tam Khương facts not mixed into operational documents | PASS |  |
| every document cites a source in source_manifest | PASS |  |
| no duplicate documents (content_hash unique) | PASS |  |
| menu has 51 items in 9 categories | PASS | 51 items |
| each item has exactly one of base_price_vnd or variants (integer VND) | PASS |  |
| no price information lost vs. bundle | PASS |  |
| no item auto-marked available | PASS |  |
| services: 3 coworking packages, 5 rooms | PASS |  |
| unverified claims recorded | PASS | 21 claims |
| no upcoming event presented as verified | PASS |  |
| no secrets in git-visible files | PASS |  |
| .env, data/cafe.db and raw/ are gitignored | PASS | .env data/cafe.db data/knowledge/raw/x |
| database file exists | PASS | E:\hackathon-cafe\hackathon\data\cafe.db |
| PRAGMA integrity_check | PASS |  |
| PRAGMA foreign_key_check | PASS |  |
| migrations 0001, 0002 applied | PASS | [1, 2] |
| every chunk has an embedding | PASS | 56/56 |
| FTS rows match chunks | PASS |  |
| embedding model/dimension = voyage-4-lite/512 | PASS | 0 mismatched |
| embeddings match current chunk content | PASS |  |
| no rejected/pending documents indexed | PASS |  |
| keyword fallback hit@5 >= 60% | PASS | 27/29 |
| SQL fact checks | PASS | 8/8 |

## Ingestion

```json
{
 "db_path": "data/cafe.db",
 "built_at": "2026-11-14T05:36:55.001Z",
 "migrations_applied_now": [],
 "documents_total": 57,
 "documents_indexed": 54,
 "documents_skipped_not_ingestible": 3,
 "chunks": 56,
 "embeddings_from_cache": 56,
 "embeddings_new": 0,
 "voyage_tokens_used": 0,
 "embedding_model": "voyage-4-lite",
 "embedding_dimension": 512,
 "menu_items": 51,
 "menu_variants": 4,
 "coworking_packages": 3,
 "meeting_rooms": 5,
 "service_facts": 22,
 "sources": 21
}
```

## Bảng trong SQLite

```json
{
 "menu_items": 51,
 "menu_item_variants": 4,
 "menu_categories": 9,
 "coworking_packages": 3,
 "meeting_rooms": 5,
 "service_facts": 22,
 "kb_sources": 21,
 "kb_documents": 54,
 "kb_chunks": 56,
 "kb_embeddings": 56,
 "kb_chunks_fts": 56
}
```

## Apify runs (chi phí thực tế do Apify báo cáo)

- `compass/crawler-google-places` run `hTvPCbgInf1lsw9ig` — usage_total_usd = 0.021199999999999997
- `clockworks/tiktok-scraper` run `qbedrS1CtnuG11vmc` — usage_total_usd = 0.07500000000000001
- **Tổng: 0.0962 USD** (ngân sách 1 USD; trần cứng mỗi run 0.50 USD qua `max_total_charge_usd`).

## Nguồn

| Source | Loại | Trạng thái | URL |
|---|---|---|---|
| `src-facebook-page` | facebook | verified_branch | https://www.facebook.com/Khonggianvanhoadongtay/ |
| `src-gmaps-listing` | google_maps | verified_branch | https://www.google.com/maps/place/Biblio+Book+Cafe+-+79+Ng%E1%BB%A5y+Nh%C6%B0+Kon+Tum/@21.0013374,105.8029646,17z |
| `src-gmaps-reviews` | google_maps_review | verified_branch | https://www.google.com/maps/place/Biblio+Book+Cafe+-+79+Ng%E1%BB%A5y+Nh%C6%B0+Kon+Tum/@21.0013374,105.8029646,17z |
| `src-kb-curation` | kb_curation | verified_branch | (local) |
| `src-photo-drink-menu` | user_photo | verified_branch | (local) |
| `src-photo-food-menu` | user_photo | verified_branch | (local) |
| `src-photo-service-board` | user_photo | verified_branch | (local) |
| `src-tiktok-bibliocafesach` | tiktok | verified_branch | https://www.tiktok.com/@bibliocafesach |
| `src-user-bundle` | user_photo | verified_branch | (local) |
| `src-web-1000libraries-2026` | web_article | verified_branch | https://magazine.1000libraries.com/9-must-visit-book-cafes-in-hanoi/ |
| `src-web-book365` | web_article | verified_branch | https://book365.vn/tintuc-sukien/top-10-quan-cafe-sach-ha-noi.html |
| `src-web-maptons` | directory_listing | unverified_branch | https://ai.maptons.com/p/15192907699 |
| `src-web-mia-2026` | web_article | verified_branch | https://mia.vn/cam-nang-du-lich/top-quan-ca-phe-sach-ha-noi-15088 |
| `src-web-restaurantguru` | directory_listing | unverified_branch | https://restaurantguru.com/Biblio-Book-Cafe-79-Nguy-Nhu-Kon-Tum-Hanoi |
| `src-web-tadiha-2022` | web_article | verified_branch | https://tadiha.com/top-3-quan-ca-phe-cho-tre-em-thoa-thich-vui-choi-o-ha-noi-d38420.htm |
| `src-web-tatinta-4357` | web_article | rejected | https://tatinta.com/diem-den/biblio-book-coffee/4357 |
| `src-web-thesmartlocal` | web_article | rejected | https://thesmartlocal.com/vietnam/book-cafes-hanoi/ |
| `src-web-topcv` | directory_listing | unverified_branch | https://www.topcv.vn/cong-ty/ca-phe-sach-biblio/56405.html |
| `src-web-toplist` | web_article | brand_general | https://toplist.vn/top-list/quan-cafe-sach-dep-nhat-danh-cho-mot-sach-o-ha-noi-26552.htm |
| `src-web-traveloka` | web_article | conflicting | https://www.traveloka.com/vi-vn/explore/culinary/15-quan-cafe-sach-ha-noi/161047 |
| `src-web-wanderlog` | directory_listing | rejected | https://wanderlog.com/place/details/1254145/biblio-book-coffee |

## Mạng xã hội

- TikTok: 20 video — nhận 3, chờ xác minh 6, loại 11.
- Google Maps reviews: 30 review (2022-06-15 → 2026-09-23), loại lạc đề 1; không thu thập dữ liệu cá nhân.

## Đánh giá retrieval

```json
{
 "questions": 30,
 "retrieval_questions": 29,
 "sql_checks": 8,
 "sql_pass": 8,
 "keyword_hit_at_5": 27,
 "voyage_query_tokens": 0
}
```

| Q | Path | Vector top-1 | Hit@5 | Rank | Keyword hit |
|---|---|---|---|---|---|
| q01 | kb | - | - | - | True |
| q02 | kb | - | - | - | True |
| q03 | kb | - | - | - | True |
| q04 | kb | - | - | - | True |
| q05 | kb | - | - | - | False |
| q06 | sql_services | - | - | - | True |
| q07 | kb | - | - | - | True |
| q08 | sql_services | - | - | - | True |
| q09 | sql_services | - | - | - | True |
| q10 | refuse_unverified | - | - | - | True |
| q11 | sql_menu | - | - | - | - |
| q12 | sql_menu | - | - | - | True |
| q13 | sql_menu | - | - | - | True |
| q14 | sql_menu | - | - | - | True |
| q15 | sql_menu | - | - | - | True |
| q16 | kb | - | - | - | True |
| q17 | kb | - | - | - | True |
| q18 | kb | - | - | - | True |
| q19 | kb | - | - | - | True |
| q20 | kb | - | - | - | True |
| q21 | refuse_unverified | - | - | - | True |
| q22 | kb | - | - | - | True |
| q23 | refuse_unverified | - | - | - | True |
| q24 | kb | - | - | - | True |
| q25 | kb | - | - | - | True |
| q26 | refuse_unverified | - | - | - | True |
| q27 | refuse_unverified | - | - | - | True |
| q28 | refuse_unverified | - | - | - | True |
| q29 | kb | - | - | - | True |
| q30 | kb | - | - | - | False |

SQL checks: q06=PASS, q08=PASS, q09=PASS, q11=PASS, q12=PASS, q13=PASS, q14=PASS, q15=PASS

## Còn thiếu / chưa xác minh

- Tình trạng còn/hết của toàn bộ 51 món (availability=unknown). (`src-user-bundle`)
- Giá trên ảnh menu/bảng dịch vụ có còn hiện hành. (`src-user-bundle`)
- Lựa chọn nóng/lạnh, đường, đá cho từng món. (`src-photo-drink-menu`)
- Thành phần, độ ngọt, caffeine, dị ứng của từng món. (`src-user-bundle`)
- Ý nghĩa dấu X viết tay cạnh 'Trà xoài Yakult'. (`src-photo-drink-menu`)
- Tên chính xác của món 'Bơ già dừa non'. (`src-photo-drink-menu`)
- Chính tả 'chesse' trong 'Olong đào kem chesse', 'Matcha kem chesse'. (`src-photo-drink-menu`)
- Tên và cách phục vụ 'Trà xuân 1/2 người'. (`src-photo-drink-menu`)
- Lịch trống phòng hội thảo; chính sách đặt cọc/hủy. (`src-photo-service-board`)
- Điều kiện giảm 25% hóa đơn đồ uống cho khách co-working (gói nào, cộng dồn?). (`src-photo-service-board`)
- Phạm vi 'Bố trí, decor theo sở thích'. (`src-photo-service-board`)
- Giá backdrop/standee. (`src-photo-service-board`)
- Thẻ mượn sách: còn áp dụng? giá? (nguồn 2022). (`src-web-tadiha-2022`)
- Phí gửi xe (Google Maps chỉ ghi 'có tính phí'). (`src-gmaps-listing`)
- Khu trẻ em/khu tô tượng hiện còn hoạt động? giờ, phí? (`src-web-book365`)
- Lịch sự kiện sắp tới (fanpage không truy cập được). (`src-facebook-page`)
- Email cafesachbiblio@gmail.com còn dùng? (nguồn 2022). (`src-web-tadiha-2022`)
- Diện tích 'hơn 1000m²' (bài tổng hợp, không ghi ngày). (`src-web-book365`)
- Quan hệ với 'Không gian văn hóa Đông Tây' / 'Cafe sách Đông Tây'. (`src-web-traveloka`)
- '79a Ngụy Như Kon Tum' trong video Civilis có phải chi nhánh này? (`src-tiktok-bibliocafesach`)
- Mật khẩu Wi-Fi (có trên ảnh nhưng cố ý không lưu). (`src-photo-drink-menu`)
