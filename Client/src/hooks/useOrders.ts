import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchOrder, fetchOrders, placeOrder } from "../api/orders";
import type { OrderListQuery } from "../api/types";

export function useOrders(query: OrderListQuery) {
  return useQuery({
    queryKey: ["orders", query],
    queryFn: () => fetchOrders(query),
    placeholderData: keepPreviousData,
  });
}

export function useOrder(orderId: number) {
  return useQuery({
    queryKey: ["orders", orderId],
    queryFn: () => fetchOrder(orderId),
    enabled: Number.isInteger(orderId) && orderId >= 1,
  });
}

export function usePlaceOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: placeOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}
