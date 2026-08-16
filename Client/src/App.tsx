import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Layout from "./components/Layout";
import { AdminRoute, ProtectedRoute } from "./components/ProtectedRoute";
import AdminBookFormPage from "./pages/AdminBookFormPage";
import AdminBooksPage from "./pages/AdminBooksPage";
import AdminOrdersPage from "./pages/AdminOrdersPage";
import BookDetailPage from "./pages/BookDetailPage";
import CartPage from "./pages/CartPage";
import CheckoutPage from "./pages/CheckoutPage";
import ForgotPage from "./pages/ForgotPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import OrderDetailPage from "./pages/OrderDetailPage";
import OrdersPage from "./pages/OrdersPage";
import RegisterPage from "./pages/RegisterPage";
import ResetPage from "./pages/ResetPage";

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/books/:id", element: <BookDetailPage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
      { path: "/forgot", element: <ForgotPage /> },
      { path: "/reset", element: <ResetPage /> },
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/cart", element: <CartPage /> },
          { path: "/checkout", element: <CheckoutPage /> },
          { path: "/orders", element: <OrdersPage /> },
          { path: "/orders/:id", element: <OrderDetailPage /> },
        ],
      },
      {
        element: <AdminRoute />,
        children: [
          { path: "/admin/books", element: <AdminBooksPage /> },
          { path: "/admin/books/new", element: <AdminBookFormPage /> },
          { path: "/admin/books/:id/edit", element: <AdminBookFormPage /> },
          { path: "/admin/orders", element: <AdminOrdersPage /> },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
