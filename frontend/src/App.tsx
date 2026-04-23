import { Routes, Route } from "react-router-dom";

function HomePage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-primary">parcer</h1>
        <p className="mt-2 text-muted-foreground">AI-платформа для лидогенерации</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  );
}
