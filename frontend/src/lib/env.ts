import type { HassObject, HassUser } from "../hass/types";

export const IS_DEMO: boolean =
  typeof window !== "undefined" &&
  (new URLSearchParams(window.location.search).get("demo") === "1" ||
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1");

export function getDemoUser(): HassUser {
  return {
    id: "demo-user",
    name: "Anthony",
    is_owner: true,
    is_admin: true,
  };
}

export function getDemoHass(): HassObject {
  return {
    user: getDemoUser(),
    language: "en",
    themes: { darkMode: true },
    states: {},
  };
}
