import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { authApi } from "../services/api";
import { User, AuthStatus } from "../types";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  signin: (username: string, password: string) => Promise<void>;
  signup: (
    username: string,
    password: string,
    systemPassword: string
  ) => Promise<void>;
  signout: () => Promise<void>;
  updateProfile: (password?: string, systemPassword?: string) => Promise<void>;
  checkAuthStatus: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  const signin = async (username: string, password: string) => {
    try {
      await authApi.signin({ username, password });
      await checkAuthStatus();
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || "Sign in failed");
    }
  };

  const signup = async (
    username: string,
    password: string,
    systemPassword: string
  ) => {
    try {
      await authApi.signup({
        username,
        password,
        system_password: systemPassword,
      });
      await checkAuthStatus();
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || "Sign up failed");
    }
  };

  const signout = async () => {
    try {
      await authApi.signout();
      setUser(null);
    } catch (error: any) {
      console.error("Sign out error:", error);
      // Even if the API call fails, clear the local state
      setUser(null);
    }
  };

  const updateProfile = async (password?: string, systemPassword?: string) => {
    try {
      const updatedUser = await authApi.updateProfile({
        password,
        system_password: systemPassword,
      });
      setUser(updatedUser);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || "Profile update failed");
    }
  };

  const checkAuthStatus = async () => {
    try {
      setIsLoading(true);
      const authStatus: AuthStatus = await authApi.checkAuthStatus();
      if (authStatus.authenticated && authStatus.user) {
        setUser({
          id: authStatus.user.id,
          username: authStatus.user.username,
          is_active: authStatus.user.is_active,
          created_at: "", // This will be fetched if needed
          updated_at: undefined,
        });
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    signin,
    signup,
    signout,
    updateProfile,
    checkAuthStatus,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
