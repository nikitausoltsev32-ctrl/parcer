export default function ChatPage() {
  return (
    <div className="flex h-full flex-col">
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl space-y-4 text-muted-foreground">
          Привет. Расскажите, кого вы ищете — и я подберу компании, напишу письма и буду вести их.
        </div>
      </main>
      <footer className="border-t p-4">
        <div className="mx-auto flex max-w-3xl gap-2">
          <input
            className="flex-1 rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
            placeholder="Например: нужны клиенты для дизайн-студии в Казани"
          />
          <button className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground">
            Отправить
          </button>
        </div>
      </footer>
    </div>
  );
}
