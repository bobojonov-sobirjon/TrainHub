export type UserPublic = {
  id: number;
  public_id: string;
  email: string | null;
  phone: string | null;
  first_name: string;
  last_name: string;
  avatar_url: string | null;
  gender: string | null;
  roles: string[];
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserPublic;
};

export type SuccessResponse<T> = {
  success: true;
  data: T;
};

export type ErrorResponse = {
  success: false;
  error: {
    code: string;
    message: string;
  };
};

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type DashboardStats = {
  users: number;
  trainers: number;
  clients: number;
  active_sessions: number;
  active_subscriptions: number;
};

export type DictionaryItem = {
  category: string;
  code: string;
  title_ru: string;
  sort_order: number;
};

export type DictionariesData = {
  items: DictionaryItem[];
};
