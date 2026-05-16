// ─── Auth Types ───────────────────────────────────────────────────────────────
// Mirrors backend DTOs exactly:
//   modules/auth/dto/request.py  → LoginRequest, CreateAdminRequest
//   modules/auth/dto/response.py → TokenResponse, AdminResponse, MessageResponse

export interface LoginRequest {
  username: string;
  password: string;
}

export interface CreateAdminRequest {
  username: string;
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string; // "bearer"
  expires_in: number; // seconds
}

export interface AdminResponse {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
}

export interface MessageResponse {
  message: string;
}
