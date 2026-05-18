## 2024-05-24 - High-Frequency Event Array Processing Lag
**Learning:** Attaching high-frequency event listeners (like tracking exact `onMouseMove` coordinates) in components that perform O(N) array transformations (like `leads.map` recalculating strings, filters, and slices on each lead) causes severe render lag and UI freezing.
**Action:** Always memoize array transformations (with `useMemo`) *before* returning JSX if the component state updates frequently, separating the expensive data normalization from the rapid render cycle.
