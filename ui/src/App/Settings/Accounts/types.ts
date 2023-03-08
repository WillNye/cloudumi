export type Group = {
  id: string;
  name: string;
  description: string;
  managed_by: string;
  users: string[];
};

export type User = {
  id: string;

  email: string;
  username: string;
  managed_by: string;
  groups: string[];
};
