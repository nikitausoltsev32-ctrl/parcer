## 2024-05-15 - React List Memoization Optimization
**Learning:** Frequent small state changes (like `hoveredName` tracking cursor position) in components rendering long arrays cause expensive $O(N)$ re-filtering and derived array recreations if not properly memoized.
**Action:** When working on React list components with frequent interactive state changes, defensively wrap derived lists (`companies`, `filtered`) in `useMemo` and hoist static calculations like `search.toLowerCase()` outside the `.filter` loop to shift string allocation from $O(N)$ to $O(1)$.
