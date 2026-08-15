import { useQuery } from "@tanstack/react-query";
import { fetchCart } from "../api/cart";
import { useAuth } from "../context/AuthContext";

export function useCart() {
  const { status } = useAuth();
  return useQuery({
    queryKey: ["cart"],
    queryFn: fetchCart,
    enabled: status === "authenticated",
  });
}
