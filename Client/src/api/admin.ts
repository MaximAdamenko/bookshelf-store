import { api, toQueryString } from "./client";
import type {
  AdminOrderListResponse,
  AdminOrderSummary,
  AdminOrderTarget,
  AuthorCreateInput,
  AuthorRef,
  BookCreateInput,
  BookListResponse,
  BookPatchInput,
  BookPublic,
  BookSearchQuery,
  OrderListQuery,
} from "./types";

export const adminFetchBooks = (query: BookSearchQuery) =>
  api<BookListResponse>(`/admin/books${toQueryString(query)}`);

export const adminFetchBook = (bookId: number) => api<BookPublic>(`/admin/books/${bookId}`);

export const createBook = (input: BookCreateInput) =>
  api<BookPublic>("/admin/books", { method: "POST", body: input });

export const patchBook = (bookId: number, input: BookPatchInput) =>
  api<BookPublic>(`/admin/books/${bookId}`, { method: "PATCH", body: input });

export const deleteBook = (bookId: number) =>
  api<void>(`/admin/books/${bookId}`, { method: "DELETE" });

export const uploadCover = (bookId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api<BookPublic>(`/admin/books/${bookId}/cover`, { method: "POST", body: form });
};

export const createAuthor = (input: AuthorCreateInput) =>
  api<AuthorRef>("/admin/authors", { method: "POST", body: input });

export const adminFetchOrders = (query: OrderListQuery) =>
  api<AdminOrderListResponse>(`/admin/orders${toQueryString(query)}`);

export const setOrderStatus = (orderId: number, status: AdminOrderTarget) =>
  api<AdminOrderSummary>(`/admin/orders/${orderId}/status`, {
    method: "PATCH",
    body: { status },
  });
