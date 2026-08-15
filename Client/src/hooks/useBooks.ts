import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchBook, fetchBooks, fetchCategories } from "../api/books";
import type { BookSearchQuery } from "../api/types";

export function useBooks(query: BookSearchQuery) {
  return useQuery({
    queryKey: ["books", query],
    queryFn: () => fetchBooks(query),
    placeholderData: keepPreviousData,
  });
}

export function useBook(bookId: number) {
  return useQuery({
    queryKey: ["books", bookId],
    queryFn: () => fetchBook(bookId),
    enabled: Number.isInteger(bookId) && bookId >= 1,
  });
}

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
    staleTime: 5 * 60_000,
  });
}
