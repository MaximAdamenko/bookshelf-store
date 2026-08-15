import { api } from "./client";
import type { ChallengeResponse, DetailResponse, TokenResponse, UserPublic } from "./types";

export interface RegisterInput {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  birth_date?: string;
  phone?: string;
}

export const register = (input: RegisterInput) =>
  api<UserPublic>("/auth/register", { method: "POST", body: input });

export const login = (email: string, password: string) =>
  api<ChallengeResponse>("/auth/login", { method: "POST", body: { email, password } });

export const verifyLogin = (challenge_token: string, code: string) =>
  api<TokenResponse>("/auth/login/verify", { method: "POST", body: { challenge_token, code } });

export const forgotPassword = (email: string) =>
  api<DetailResponse>("/auth/forgot", { method: "POST", body: { email } });

export const resetPassword = (token: string, new_password: string) =>
  api<DetailResponse>("/auth/reset", { method: "POST", body: { token, new_password } });

export const fetchMe = () => api<UserPublic>("/auth/me");
