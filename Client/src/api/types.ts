export interface UserPublic {
  user_id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: "admin" | "customer";
  email_verified: boolean;
  created_at: string;
}

export interface ChallengeResponse {
  challenge_token: string;
  expires_in: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface DetailResponse {
  detail: string;
}

export interface AuthorRef {
  author_id: number;
  name: string;
}

export interface AuthorCreateInput {
  first_name: string;
  last_name: string;
}

export interface CategoryRef {
  category_id: number;
  name: string;
}

export interface PublisherRef {
  publisher_id: number;
  name: string;
}

export interface BookPublic {
  book_id: number;
  title: string;
  description: string;
  price_cents: number;
  quantity: number;
  cover_path: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  publisher_id: number | null;
  publisher: string | null;
  authors: AuthorRef[];
  categories: CategoryRef[];
}

export interface BookListResponse {
  items: BookPublic[];
  total: number;
}

export type BookSort = "newest" | "price_asc" | "price_desc" | "relevance";

export interface BookSearchQuery {
  q?: string;
  category_id?: number;
  min_price_cents?: number;
  max_price_cents?: number;
  in_stock?: boolean;
  sort?: BookSort;
  limit?: number;
  offset?: number;
}

export interface CartLine {
  cart_item_id: number;
  book_id: number;
  title: string;
  cover_path: string | null;
  unit_price_cents: number;
  quantity: number;
  line_total_cents: number;
  stock_remaining: number;
  is_available: boolean;
}

export interface CartResponse {
  items: CartLine[];
  item_count: number;
  subtotal_cents: number;
  has_unavailable_lines: boolean;
}

export type OrderStatus = "pending" | "paid" | "shipped" | "cancelled";

export interface ShippingInput {
  first_name: string;
  last_name: string;
  street: string;
  city: string;
  apartment?: string;
  postal_code: string;
  phone?: string;
}

export interface ShippingSnapshot {
  first_name: string;
  last_name: string;
  street: string;
  city: string;
  apartment: string | null;
  postal_code: string;
  phone: string | null;
}

export interface OrderItemPublic {
  order_item_id: number;
  book_id: number | null;
  title: string;
  authors: string;
  unit_price_cents: number;
  quantity: number;
  total_price_cents: number;
}

export interface OrderPublic {
  order_id: number;
  status: OrderStatus;
  amount_cents: number;
  order_date: string;
  shipping: ShippingSnapshot;
  items: OrderItemPublic[];
}

export interface OrderSummary {
  order_id: number;
  status: OrderStatus;
  amount_cents: number;
  item_count: number;
  order_date: string;
}

export interface OrderListResponse {
  items: OrderSummary[];
  total: number;
}

export interface OrderListQuery {
  status?: OrderStatus;
  limit?: number;
  offset?: number;
}

export interface BookCreateInput {
  title: string;
  description: string;
  price_cents: number;
  quantity: number;
  author_ids: number[];
  category_ids: number[];
  publisher_id?: number | null;
}

export interface BookPatchInput {
  title?: string;
  description?: string;
  price_cents?: number;
  quantity?: number;
  is_active?: boolean;
  author_ids?: number[];
  category_ids?: number[];
  publisher_id?: number | null;
}

export type AdminOrderTarget = Exclude<OrderStatus, "pending">;

export interface AdminOrderSummary extends OrderSummary {
  user_id: number;
  email: string;
}

export interface AdminOrderListResponse {
  items: AdminOrderSummary[];
  total: number;
}
