import { useMutation, useQueryClient } from "@tanstack/react-query";
import { addToCart } from "../api/cart";

export function useAddToCart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ bookId, quantity }: { bookId: number; quantity: number }) =>
      addToCart(bookId, quantity),
    onSuccess: (cart) => queryClient.setQueryData(["cart"], cart),
  });
}
