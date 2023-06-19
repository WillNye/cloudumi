export interface ProviderData {
  provider: string;
  sub_type: string;
}

export interface ApiResponse {
  status_code: number;
  data: ProviderData[];
}

export interface ProviderDetails {
  title: string;
  icon: string;
  description: string;
}

export interface Provider {
  provider: string;
  title: string;
  icon: string;
  description: string;
}
