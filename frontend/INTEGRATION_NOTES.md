# Dev B → Dev A integration notes

Backend snapshot tested: `81648a3` (`feat/dev-a-backend-agent`), immutable copy under ignored `frontend/node_modules/.cache/`.
Frontend live mode, separate SQLite backup of the ingested catalogue. Main has not been merged; Dev A is still implementing.

## Admin SSE omits allowed_next (found in real C4 run)

- `backend/app/api/admin.py:update_status` returns `admin_order(order)` via REST, but publishes `{"order": order}` to the admin bus.
- `orders/service.py` supplies the customer order shape without `allowed_next`. Consequently `GET /api/admin/stream` sends status updates without permitted actions, while `GET /api/admin/orders` and PATCH responses include them.
- User-visible effect: after **Nhận đơn**, the subsequent SSE update removed **Đang pha** / **Sẵn sàng** buttons. The first live AI rehearsal stopped here after two successful model turns and one confirmed draft order.
- Frontend mitigation: if an admin stream event omits optional `allowed_next`, refetch the authenticated admin list; never infer permissions locally. Regression: `src/admin/state/useAdminStream.test.ts`, RED reproduced before fix.
- Suggested Dev A correction: publish `admin_order(order)` on the **admin** topic (keep the customer topic shape unchanged). No contract/schema edits requested or made by Dev B.

## Verified before this correction

- Live catalogue: 51 items, health 56 chunks, configured model/admin.
- Live UI checkout `BB-0001`, admin confirmation, customer update in 64ms.
- Real agent returned grounded recommendations, used prepare_order, produced 45.000đ draft, REST created `BB-0002`; no order was represented as created before REST success.

## C4 passed after client mitigation

- Live agent rehearsal on the same backend snapshot passed for `BB-0003`: three real user turns, grounded recommendations, 45.000đ draft, REST confirm, admin confirmed→preparing→ready, customer tracking, then agent get_order_status reporting ready.
- Main remains unmerged by owner instruction; these are snapshot integration results, not combined-main acceptance.

## P1 insights client omission

Contract §7 defines GET /api/admin/insights, §9 defines AdminInsights, and Dev A 9e0a3b1 implements it, but §10 ApiClient lists no insights method. Dev B preserves §10 verbatim and isolates the P1 adapter in src/api/insights.ts over the same request/auth/error layer. Mock mode reports live-required rather than inventing analytics.
