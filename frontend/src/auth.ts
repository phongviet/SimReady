export interface Principal {
  user_id: string;
  display_name: string;
  role: "builder" | "reviewer";
}
export function accountToken() {
  return typeof window === "undefined"
    ? ""
    : sessionStorage.getItem("simready-token") || "";
}
export function setAccountToken(token: string) {
  if (token) sessionStorage.setItem("simready-token", token);
  else sessionStorage.removeItem("simready-token");
}
