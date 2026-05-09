## 2024-05-18 - Memoizing derived state in React components
**Learning:** When using `useMemo` to optimize derived state like filtered lists, ensure that the dependencies are also memoized. In `CompaniesPage.tsx`, `companies` was derived from `contacts` on every render, which negated the benefit of memoizing the `filtered` list that depended on `companies`.
**Action:** Always verify the stability of dependencies array passed to `useMemo` and `useCallback`. If a dependency changes on every render, it must be memoized too.
