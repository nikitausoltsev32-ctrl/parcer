import { useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useVerifyEmail } from "../features/auth/hooks";

export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const sent = params.get("sent");
  const verify = useVerifyEmail();

  useEffect(() => {
    if (token) verify.mutate(token);
  }, [token]);

  if (sent) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-sm text-center space-y-3">
          <h1 className="text-2xl font-semibold">Проверьте почту</h1>
          <p className="text-muted-foreground text-sm">
            Мы отправили письмо с ссылкой для подтверждения. Перейдите по ссылке, чтобы войти.
          </p>
        </div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <p className="text-muted-foreground text-sm">Неверная ссылка.</p>
      </div>
    );
  }

  if (verify.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <p className="text-muted-foreground text-sm">Подтверждаем email...</p>
      </div>
    );
  }

  if (verify.isError) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-sm text-center space-y-3">
          <h1 className="text-xl font-semibold text-destructive">Ссылка недействительна</h1>
          <p className="text-sm text-muted-foreground">
            Возможно, она уже использована или истекла.
          </p>
          <Link to="/login" className="text-sm text-primary hover:underline">
            Войти
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="max-w-sm text-center space-y-3">
        <h1 className="text-2xl font-semibold">Email подтверждён</h1>
        <p className="text-sm text-muted-foreground">Теперь вы можете войти в аккаунт.</p>
        <Link to="/login" className="block text-sm text-primary hover:underline">
          Войти
        </Link>
      </div>
    </div>
  );
}
