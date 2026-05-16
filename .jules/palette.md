## 2024-05-16 - Add missing ARIA labels
**Learning:** Found several icon-only buttons (like delete buttons and close buttons) that lacked accessibility labels. When doing UX improvements, ensuring these standard interactive elements have `aria-label` or `title` is a very basic but necessary check.
**Action:** Always check `aria-label` and `title` attributes for buttons containing only icons or SVGs in any components touched, particularly in dynamic lists or modal windows.
