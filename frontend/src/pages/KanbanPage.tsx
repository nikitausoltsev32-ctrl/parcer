import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { G } from "../lib/design";

interface Contact {
  id: string;
  contact_name: string;
  company_name?: string;
  status: string;
  email: string | null;
  phone: string | null;
  enrichment: Record<string, unknown> | null;
}

const COLUMNS = [
  { id: "new", title: "Новые лиды", color: G.blue },
  { id: "contacted", title: "В работе (Contacted)", color: G.amber },
  { id: "replied", title: "Ответили (Replied)", color: G.green },
  { id: "qualified", title: "Квалифицированы", color: "#6366f1" },
  { id: "won", title: "Успех (Won)", color: "#10b981" },
  { id: "lost", title: "Отказ (Lost)", color: G.red },
];

export default function KanbanPage() {
  const queryClient = useQueryClient();
  const [draggedContact, setDraggedContact] = useState<Contact | null>(null);

  const { data: contacts = [], isLoading } = useQuery<Contact[]>({
    queryKey: ["contacts_kanban"],
    queryFn: () => api.get("/contacts", { params: { limit: 500 } }).then(r => r.data),
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => 
      api.patch(`/contacts/${id}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts_kanban"] });
    }
  });

  const handleDragStart = (contact: Contact) => setDraggedContact(contact);
  const handleDragOver = (e: React.DragEvent) => e.preventDefault();
  const handleDrop = (status: string) => {
    if (draggedContact && draggedContact.status !== status) {
      // Optimistic update
      queryClient.setQueryData<Contact[]>(["contacts_kanban"], (old) => 
        old?.map(c => c.id === draggedContact.id ? { ...c, status } : c)
      );
      updateStatus.mutate({ id: draggedContact.id, status });
    }
    setDraggedContact(null);
  };

  if (isLoading) return <div style={{ padding: "40px", color: G.textMuted }}>Загрузка Канбана...</div>;

  return (
    <div style={{ padding: "24px", height: "100%", display: "flex", flexDirection: "column" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 700, color: G.textPrimary, marginBottom: "20px" }}>Канбан-доска</h1>
      <p style={{ fontSize: "14px", color: G.textMuted, marginBottom: "24px" }}>
        Перетаскивайте карточки лидов между колонками для изменения их статуса.
      </p>

      <div style={{ display: "flex", gap: "16px", flex: 1, overflowX: "auto", paddingBottom: "16px" }}>
        {COLUMNS.map(col => {
          const colContacts = contacts.filter(c => c.status === col.id);
          return (
            <div 
              key={col.id} 
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(col.id)}
              style={{
                width: "300px", minWidth: "300px", flexShrink: 0,
                background: "rgba(26, 37, 64, 0.03)", borderRadius: G.radius,
                border: G.border, display: "flex", flexDirection: "column",
                maxHeight: "100%",
              }}
            >
              <div style={{ padding: "16px", borderBottom: G.borderSubtle, display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: col.color }} />
                <span style={{ fontSize: "14px", fontWeight: 600, color: G.textPrimary }}>{col.title}</span>
                <span style={{ marginLeft: "auto", fontSize: "12px", color: G.textMuted, background: "rgba(0,0,0,0.05)", padding: "2px 6px", borderRadius: "10px" }}>
                  {colContacts.length}
                </span>
              </div>

              <div style={{ padding: "12px", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: "12px" }}>
                {colContacts.map(c => (
                  <div
                    key={c.id}
                    draggable
                    onDragStart={() => handleDragStart(c)}
                    style={{
                      background: G.glassCard, borderRadius: G.radiusSm, border: G.borderSubtle,
                      padding: "12px", boxShadow: G.shadowCard, cursor: "grab",
                      transition: "transform 0.1s",
                    }}
                    onDragEnd={() => setDraggedContact(null)}
                  >
                    <div style={{ fontSize: "14px", fontWeight: 600, color: G.textPrimary, marginBottom: "4px" }}>
                      {c.company_name || c.contact_name || "Неизвестно"}
                    </div>
                    {c.company_name && c.contact_name && (
                      <div style={{ fontSize: "12px", color: G.textMuted, marginBottom: "8px" }}>{c.contact_name}</div>
                    )}
                    {(c.email || c.phone) && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "8px", borderTop: "1px dashed rgba(0,0,0,0.1)", paddingTop: "8px" }}>
                        {c.email && <div style={{ fontSize: "11px", color: G.textMuted, fontFamily: "monospace" }}>{c.email}</div>}
                        {c.phone && <div style={{ fontSize: "11px", color: G.textMuted, fontFamily: "monospace" }}>{c.phone}</div>}
                      </div>
                    )}
                  </div>
                ))}
                {colContacts.length === 0 && (
                  <div style={{ textAlign: "center", padding: "20px", color: G.textMuted, fontSize: "12px" }}>Нет лидов</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
