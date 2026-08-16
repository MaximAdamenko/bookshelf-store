import { api, BASE_URL, toQueryString } from "./client";
import type {
  AuthorRef,
  BookListResponse,
  BookPublic,
  BookSearchQuery,
  CategoryRef,
  PublisherRef,
} from "./types";

export const fetchBooks = (query: BookSearchQuery) =>
  api<BookListResponse>(`/books${toQueryString(query)}`);

export const fetchBook = (bookId: number) => api<BookPublic>(`/books/${bookId}`);

export const fetchCategories = () => api<CategoryRef[]>("/categories");

export const fetchAuthors = () => api<AuthorRef[]>("/authors");

export const fetchPublishers = () => api<PublisherRef[]>("/publishers");

export const coverUrl = (filename: string) =>
  `${BASE_URL}/media/covers/${encodeURIComponent(filename)}`;
