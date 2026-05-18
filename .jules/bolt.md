## 2023-11-20 - Memoizing list processes before mouse tracking

**Learning:** When components track high-frequency events like mouse movements (e.g., `onMouseMove` updating `hoverPos`) and also render long lists, O(N) data transformation processes (like string manipulations and filtering) inside the render loop create severe performance bottlenecks.
**Action:** Always wrap data transformations over lists inside `useMemo` when the component also tracks hover/scroll position state, to prevent re-computing data for every single pixel of mouse movement.
