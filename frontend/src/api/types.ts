export type Availability = "available" | "sold_out" | "unknown";
export type VerificationStatus = "owner_verified" | "verified_branch" | "brand_general" | "unverified_branch" | "conflicting";
export type OrderStatus = "pending" | "confirmed" | "preparing" | "ready" | "completed" | "rejected" | "cancelled";
export type AgentState = "idle" | "thinking" | "searching" | "working" | "composing" | "error";

export interface ApiErrorBody { error: { code: string; message: string; details?: Record<string, unknown> } }

export interface SourceRef { source_id: string; title: string; url: string | null; retrieved_at: string; verification_status: VerificationStatus }

export interface CafeProfile {
  branch_id: string; brand_name: string; display_name: string;
  address: string; latitude: number; longitude: number; plus_code: string;
  phone: string; opening_hours: { open: string; close: string; days_label: string }; is_open_now: boolean;
  channels: { google_maps_url: string; facebook_url: string; tiktok_url: string; website_url: string | null };
  wifi: { available: boolean; ssid: string; password_policy: "ask_staff" };
  rating_snapshot: { rating: number; reviews_count: number; as_of: string; source_id: string } | null;
  highlights: { label: string; source_id: string }[];
  data_status: "owner_verified" | "user_provided_unverified"; data_notice: string;
  sources: SourceRef[];
}

export interface MenuVariant { id: string; label: string; price_vnd: number }
export interface MenuItem {
  id: string; category_id: string; name: string;
  price_vnd: number | null; price_min_vnd: number; price_max_vnd: number; variants: MenuVariant[];
  availability: Availability; availability_note: string | null; is_orderable: boolean; price_verified: boolean;
  description: string | null; needs_review: string[]; suggested_tags: string[];
}
export interface MenuCategory { id: string; name: string; kind: "drink" | "food"; sort_order: number; item_count: number }
export interface MenuResponse { as_of: string; price_basis: string; categories: MenuCategory[]; items: MenuItem[] }

export interface CoworkingPackage { id: string; label: string; duration_days: number; price_vnd: number; includes_vat: boolean; price_verified: boolean }
export interface MeetingRoom {
  id: string; name: string; area_m2: number; capacity_max: number; capacity_theater: number | null; capacity_tables: number | null;
  layout_note: string; session_hours: number; price_vnd: number; includes_vat: boolean; price_verified: boolean;
}
export interface ServiceFact {
  id: string; scope: "coworking" | "meeting_room" | "cafe"; kind: "amenity" | "extra_service" | "policy"; label: string;
  price_from_vnd: number | null; price_to_vnd: number | null; unit: string | null; note: string | null;
}
export interface ServicesResponse { as_of: string; price_basis: string; coworking_packages: CoworkingPackage[]; meeting_rooms: MeetingRoom[]; facts: ServiceFact[]; booking_policy: string }

export interface CartLineInput { item_id: string; variant_id: string | null; quantity: number; note?: string | null }
export interface QuoteLine {
  line_no: number; item_id: string; variant_id: string | null; item_name: string; variant_label: string | null;
  unit_price_vnd: number; quantity: number; line_total_vnd: number; availability: Availability; note: string | null;
}
export interface QuoteWarning { code: "AVAILABILITY_UNCONFIRMED" | "PRICE_UNVERIFIED"; message: string; item_ids: string[] }
export interface OrderQuote { lines: QuoteLine[]; subtotal_vnd: number; total_vnd: number; item_count: number; currency: "VND"; warnings: QuoteWarning[]; quoted_at: string }

export interface CreateOrderRequest {
  lines: CartLineInput[]; expected_total_vnd: number;
  customer_name?: string | null; table_label?: string | null; note?: string | null;
}
export interface OrderDraft {
  draft_id: string; status: "open" | "confirmed" | "discarded"; quote: OrderQuote;
  customer_name: string | null; table_label: string | null; note: string | null;
  order_code: string | null; created_at: string; expires_at: string;
}
export interface OrderEvent { from_status: OrderStatus | null; to_status: OrderStatus; actor: "customer" | "admin" | "system"; note: string | null; created_at: string }
export interface OrderLine {
  line_no: number; item_id: string; variant_id: string | null; item_name: string; variant_label: string | null;
  unit_price_vnd: number; quantity: number; line_total_vnd: number; note: string | null;
}
export interface Order {
  id: number; code: string; status: OrderStatus; status_label: string; source: "ui" | "agent_draft";
  customer_name: string | null; table_label: string | null; note: string | null;
  lines: OrderLine[]; subtotal_vnd: number; total_vnd: number; item_count: number;
  status_reason: string | null; created_at: string; updated_at: string; events: OrderEvent[];
  allowed_next?: OrderStatus[];            // present only in admin responses
}

export interface AdminLoginResponse { token: string; expires_at: string }
export interface AdminOrderListResponse { orders: Order[]; counts: Record<OrderStatus, number> }
export interface UpdateOrderStatusRequest { to_status: OrderStatus; expected_status: OrderStatus; reason?: string | null }
export interface UpdateMenuItemRequest { availability?: Availability; availability_note?: string | null; is_orderable?: boolean }
export interface AdminInsights {
  orders_by_status: Record<OrderStatus, number>; orders_total: number; revenue_completed_vnd: number;
  top_items: { item_id: string; name: string; quantity: number }[];
  agent: { runs: number; tool_calls: Record<string, number>; tool_errors: number; input_tokens: number; output_tokens: number };
}

export type AgentStreamEvent =
  | { event: "run_started"; data: { run_id: string } }
  | { event: "agent_state"; data: { state: AgentState } }
  | { event: "tool_started"; data: { call_id: string; tool: string; label: string } }
  | { event: "tool_finished"; data: { call_id: string; tool: string; ok: boolean; summary: string } }
  | { event: "order_draft"; data: { draft: OrderDraft } }
  | { event: "text_delta"; data: { delta: string } }
  | { event: "message_completed"; data: { text: string; sources: SourceRef[] } }
  | { event: "error"; data: { code: string; message: string; retryable: boolean } }
  | { event: "done"; data: { reason: "completed" | "error" | "cancelled"; usage: { input_tokens: number; output_tokens: number; requests: number } } };

export type OrderStreamEvent = { event: "order_status"; data: { order: Order } };
export type AdminStreamEvent = { event: "order_created"; data: { order: Order } } | { event: "order_updated"; data: { order: Order } };

export type StaffRequestKind = "wifi" | "clean_table" | "water" | "find_book" | "payment" | "temperature" | "other";
export interface StaffRequest {
  id: number; code: string; kind: StaffRequestKind; kind_label: string; table_label: string | null; note: string | null;
  status: "open" | "done"; status_label: string; created_at: string; resolved_at: string | null;
}
export interface StaffRequestListResponse { requests: StaffRequest[] }
export type StaffStreamEvent = { event: "staff_request_created" | "staff_request_updated"; data: { request: StaffRequest } };
