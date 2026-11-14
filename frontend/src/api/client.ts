import type { CafeProfile, MenuResponse, ServicesResponse, CartLineInput, OrderQuote, CreateOrderRequest, Order, OrderStreamEvent, AgentStreamEvent, AdminLoginResponse, OrderStatus, AdminOrderListResponse, UpdateOrderStatusRequest, UpdateMenuItemRequest, MenuItem, AdminStreamEvent } from './types';

export interface ApiClient {
  getCafe(): Promise<CafeProfile>;
  getMenu(params?: { category?: string; q?: string; max_price_vnd?: number }): Promise<MenuResponse>;
  getServices(): Promise<ServicesResponse>;
  quote(lines: CartLineInput[]): Promise<OrderQuote>;
  createOrder(req: CreateOrderRequest, idempotencyKey: string): Promise<Order>;
  confirmDraft(draftId: string, expectedTotalVnd: number): Promise<Order>;
  discardDraft(draftId: string): Promise<void>;
  getOrder(code: string): Promise<Order>;
  listOrders(conversationId?: string): Promise<Order[]>;
  streamOrder(code: string, onEvent: (e: OrderStreamEvent) => void, signal: AbortSignal): Promise<void>;
  chat(message: string, onEvent: (e: AgentStreamEvent) => void, signal: AbortSignal): Promise<void>;
  admin: {
    login(pin: string): Promise<AdminLoginResponse>;
    logout(): Promise<void>;
    listOrders(status?: OrderStatus): Promise<AdminOrderListResponse>;
    updateStatus(orderId: number, req: UpdateOrderStatusRequest): Promise<Order>;
    updateMenuItem(itemId: string, req: UpdateMenuItemRequest): Promise<MenuItem>;
    stream(onEvent: (e: AdminStreamEvent) => void, signal: AbortSignal): Promise<void>;
  };
}
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: Record<string, unknown>) { super(message); }
}
