export interface UserProfile {
  id: number;
  email: string;
  fullName: string;
  isActive: boolean;
}

export interface AuthSession {
  accessToken: string;
  tokenType: 'bearer';
  user: UserProfile;
}

export interface LoginRequest {
  email: string;
  password: string;
}