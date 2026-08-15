import { api, BASE_URL } from "./client";
import type { BookListResponse, BookPublic, BookSearchQuery, CategoryRef } from "./types";

export function fetchBooks(query: BookSearchQuery) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "" && value !== false) params.set(key, String(value));
  }
  const qs = params.toString();
  return api<BookListResponse>(`/books${qs ? `?${qs}` : ""}`);
}

export const fetchBook = (bookId: number) => api<BookPublic>(`/books/${bookId}`);

export const fetchCategories = () => api<CategoryRef[]>("/categories");

export const coverUrl = (filename: string) =>
  `${BASE_URL}/media/covers/${encodeURIComponent(filename)}`;
