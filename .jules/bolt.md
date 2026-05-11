## 2026-05-11 - Memoization for high-frequency events
**Learning:** Performing O(N) array transformations (like reducing and filtering) inside React functional components without `useMemo` causes severe UI lag if the component also tracks high-frequency events, such as mouse coordinates updates inside the component state on every hover event.
**Action:** Always wrap heavy data transformations and loops in `useMemo` when a component handles frequent interactive state updates that trigger full component re-renders.
