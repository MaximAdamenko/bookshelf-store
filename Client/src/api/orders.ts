import { api } from "./client";
import type { OrderListQuery, OrderListResponse, OrderPublic, ShippingInput } from "./types";

export const placeOrder = (shipping: ShippingInput) =>
  api<OrderPublic>("/orders", { method: "POST", body: shipping });

export function fetchOrders(query: OrderListQuery) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) params.set(key, String(value));
  }
  const qs = params.toString();
  return api<OrderListResponse>(`/orders${qs ? `?${qs}` : ""}`);
}

export const fetchOrder = (orderId: number) => api<OrderPublic>(`/orders/${orderId}`);
