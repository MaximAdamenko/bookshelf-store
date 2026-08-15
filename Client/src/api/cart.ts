import { api } from "./client";
import type { CartResponse } from "./types";

export const fetchCart = () => api<CartResponse>("/cart");

export const addToCart = (book_id: number, quantity: number) =>
  api<CartResponse>("/cart/items", { method: "POST", body: { book_id, quantity } });

export const updateCartItem = (cart_item_id: number, quantity: number) =>
  api<CartResponse>(`/cart/items/${cart_item_id}`, { method: "PATCH", body: { quantity } });

export const removeCartItem = (cart_item_id: number) =>
  api<void>(`/cart/items/${cart_item_id}`, { method: "DELETE" });
