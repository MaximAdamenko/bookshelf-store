import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adminFetchBook,
  adminFetchBooks,
  adminFetchOrders,
  createAuthor,
  createBook,
  deleteBook,
  hardDeleteBook,
  patchBook,
  setOrderStatus,
  uploadCover,
} from "../api/admin";
import type { AdminOrderTarget, BookPatchInput, BookSearchQuery, OrderListQuery } from "../api/types";

export function useAdminBooks(query: BookSearchQuery) {
  return useQuery({
    queryKey: ["admin", "books", query],
    queryFn: () => adminFetchBooks(query),
    placeholderData: keepPreviousData,
  });
}

export function useAdminBook(bookId: number) {
  return useQuery({
    queryKey: ["admin", "books", bookId],
    queryFn: () => adminFetchBook(bookId),
    enabled: Number.isInteger(bookId) && bookId >= 1,
  });
}

function useInvalidateBooks() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["admin", "books"] });
    queryClient.invalidateQueries({ queryKey: ["books"] });
  };
}

export function useCreateBook() {
  return useMutation({ mutationFn: createBook, onSuccess: useInvalidateBooks() });
}

export function usePatchBook() {
  return useMutation({
    mutationFn: ({ bookId, input }: { bookId: number; input: BookPatchInput }) =>
      patchBook(bookId, input),
    onSuccess: useInvalidateBooks(),
  });
}

export function useDeleteBook() {
  return useMutation({ mutationFn: deleteBook, onSuccess: useInvalidateBooks() });
}

export function useHardDeleteBook() {
  return useMutation({ mutationFn: hardDeleteBook, onSuccess: useInvalidateBooks() });
}

export function useUploadCover() {
  return useMutation({
    mutationFn: ({ bookId, file }: { bookId: number; file: File }) => uploadCover(bookId, file),
    onSuccess: useInvalidateBooks(),
  });
}

export function useCreateAuthor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createAuthor,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["authors"] }),
  });
}

export function useAdminOrders(query: OrderListQuery) {
  return useQuery({
    queryKey: ["admin", "orders", query],
    queryFn: () => adminFetchOrders(query),
    placeholderData: keepPreviousData,
  });
}

export function useSetOrderStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ orderId, status }: { orderId: number; status: AdminOrderTarget }) =>
      setOrderStatus(orderId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}
