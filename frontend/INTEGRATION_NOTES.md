# Dev B → Dev A integration notes

**Latest:** serialized integration of backend main45d28e5 + frontendec2c2de passed:91 backend tests,37 frontend tests, build,8 fixture E2E and two clean live reset/core-demo run-sets on the actual merged checkout. All C1–C5 checks are satisfied for the core demo. Main is pushed only after these checks; Dev A should fetch/merge the final origin/main into its feature branch and verify. Full details: DELIVERY_REPORT.md. Earlier snapshot observations below are retained as history.

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

## Final A5/A6 snapshot verification

- Backend 9e0a3b1: 87 default regression tests passed, 6 paid-live tests deselected.
- Two clean reset/rehearsal run-sets: each has 2 real orders, 3 completed agent runs and no error_code. Real tools include search_cafe_knowledge, search_menu, prepare_order and get_order_status; the earlier A4 run also exercised recommend_drinks. All SQL prices/draft totals came from backend.
- Final non-model smoke: 2 passed; HTTP200 idempotent replay returns the same order; customer sees staff confirmation in1098ms; admin availability saves and insights render live.
- Client loads each active status separately with limit200 so newer terminal orders do not hide older pending orders. Server counts and an incomplete-list notice expose the remaining endpoint capacity limit. Unlimited pagination needs a coordinated contract change.
- Await Dev A's main push/turn handoff. Dev B has not merged or pushed main, and has not changed backend source.
