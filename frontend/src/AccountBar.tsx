import { useEffect, useState } from "react";
import { api } from "./api";
import { accountToken, setAccountToken, type Principal } from "./auth";
export function AccountBar({
  user,
  onUser,
}: {
  user: Principal | null;
  onUser: (user: Principal | null) => void;
}) {
  const [token, setToken] = useState(""),
    [error, setError] = useState("");
  useEffect(() => {
    if (accountToken())
      api
        .me()
        .then(onUser)
        .catch((reason) => {
          setAccountToken("");
          setError(String(reason));
        });
  }, []);
  const signIn = async () => {
    try {
      const value = await api.signIn(token.trim());
      setAccountToken(token.trim());
      onUser(value);
      setToken("");
      setError("");
    } catch (reason) {
      setError(String(reason));
    }
  };
  return (
    <div className="account-bar">
      {user ? (
        <>
          <span>
            {user.display_name} · <b>{user.role}</b>
          </span>
          <button
            onClick={() => {
              setAccountToken("");
              onUser(null);
            }}
          >
            Sign out
          </button>
        </>
      ) : (
        <>
          <label>
            Local account token
            <input
              aria-label="Local account token"
              type="password"
              name="account-token"
              spellCheck={false}
              autoComplete="off"
              value={token}
              onChange={(event) => setToken(event.target.value)}
            />
          </label>
          <button onClick={() => void signIn()} disabled={!token.trim()}>
            Sign in
          </button>
          <small>
            Read tokens from your registry’s local-credentials.json. Roles are
            assigned by the server.
          </small>
        </>
      )}
      {error && <span role="alert">{error}</span>}
    </div>
  );
}
