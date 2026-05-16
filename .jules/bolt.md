## 2024-05-16 - Memoize O(N) array transformations in LeadResultsCard
**Learning:** Components in this project often track high-frequency events in state, triggering full component re-renders. If O(N) operations like mapping or filtering companies are not memoized, they cause severe UI lag.
**Action:** Always wrap O(N) array transformations inside useMemo in React components in this project.
