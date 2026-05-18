export interface HassUser {
  id: string;
  name: string;
  is_owner: boolean;
  is_admin: boolean;
}

export interface HassObject {
  user?: HassUser;
  language?: string;
  themes?: { darkMode: boolean };
  states: Record<string, unknown>;
}

export interface PanelInfo {
  component_name: string;
  url_path: string;
  title?: string;
  icon?: string;
  config?: Record<string, unknown>;
}

export interface PanelRoute {
  path: string;
  prefix: string;
}
