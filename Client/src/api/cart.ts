import { api } from "./client";
import type { CartResponse } from "./types";

export const fetchCart = () => api<CartResponse>("/cart");

export const addToCart = (book_id: number, quantity: number) =>
  api<CartResponse>("/cart/items", { method: "POST", body: { book_id, quantity } });
