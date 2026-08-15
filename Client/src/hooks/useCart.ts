import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCart, removeCartItem, updateCartItem } from "../api/cart";
import { useAuth } from "../context/AuthContext";

export function useCart() {
  const { status } = useAuth();
  return useQuery({
    queryKey: ["cart"],
    queryFn: fetchCart,
    enabled: status === "authenticated",
  });
}

export function useUpdateCartItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cartItemId, quantity }: { cartItemId: number; quantity: number }) =>
      updateCartItem(cartItemId, quantity),
    onSuccess: (cart) => queryClient.setQueryData(["cart"], cart),
  });
}

export function useRemoveCartItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: removeCartItem,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cart"] }),
  });
}
