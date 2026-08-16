import { api, toQueryString } from "./client";
import type { OrderListQuery, OrderListResponse, OrderPublic, ShippingInput } from "./types";

export const placeOrder = (shipping: ShippingInput) =>
  api<OrderPublic>("/orders", { method: "POST", body: shipping });

export const fetchOrders = (query: OrderListQuery) =>
  api<OrderListResponse>(`/orders${toQueryString(query)}`);

export const fetchOrder = (orderId: number) => api<OrderPublic>(`/orders/${orderId}`);
