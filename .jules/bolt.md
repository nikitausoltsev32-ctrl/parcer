## 2026-05-09 - [Frontend React optimization via useMemo]
**Learning:** In list views with hover effects and frequent small state changes (like CompaniesPage, ContactsPage, TemplatesPage), derived arrays using `filter` or `map` can cause heavy main thread usage if not memoized, because the components re-render rapidly on mouse events.
**Action:** Always wrap heavy list manipulations and filters with `useMemo` in React components, especially if they include real-time event handlers like `onMouseMove` which trigger re-renders.
