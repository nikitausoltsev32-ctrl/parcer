import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useLogin } from "../features/auth/hooks";

export default function LoginPage() {
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [params] = useSearchParams();
  const justRegistered = params.get("registered") === "1";

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    login.mutate({ email, password });
  }

  function handleDevLogin() {
    login.mutate({ email: "testuser5@example.com", password: "test1234" });
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-semibold">Вход</h1>

        {justRegistered && (
          <p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700 border border-green-200">
            Аккаунт создан — введите данные для входа
          </p>
        )}

        {login.isError && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            Неверный email или пароль
          </p>
        )}

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
        />
        <input
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
        />

        <button
          type="submit"
          disabled={login.isPending}
          className="w-full rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          {login.isPending ? "Входим..." : "Войти"}
        </button>

        {import.meta.env.DEV && (
          <button
            type="button"
            onClick={handleDevLogin}
            disabled={login.isPending}
            className="w-full rounded-md border border-dashed px-4 py-2 text-sm text-muted-foreground hover:bg-muted disabled:opacity-50"
          >
            [DEV] Войти как тестовый пользователь
          </button>
        )}

        <p className="text-center text-sm text-muted-foreground">
          Нет аккаунта?{" "}
          <Link to="/register" className="text-primary underline-offset-4 hover:underline">
            Зарегистрироваться
          </Link>
        </p>
        <p className="text-center text-sm text-muted-foreground">
          <Link to="/forgot-password" className="hover:underline">
            Забыли пароль?
          </Link>
        </p>
      </form>
    </div>
  );
}
