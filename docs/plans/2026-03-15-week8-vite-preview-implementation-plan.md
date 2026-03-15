# Week 8 Vite Preview Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Vite dev server to run the DORA dashboard locally and view it in a browser.

**Architecture:** Introduce Vite to the existing frontend package, add `index.html` and `src/main.tsx` to mount `App`, and configure a `/api` proxy to the metrics service.

**Tech Stack:** Vite, React 18, TypeScript

---

### Task 1: Add Vite dev server

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`

**Step 1: Write the failing test**

```python
def test_vite_config_exists():
    import os
    assert os.path.exists("frontend/vite.config.ts")
```

**Step 2: Run test to verify it fails**

Run: `python - <<'PY'
import os
assert os.path.exists("frontend/vite.config.ts")
PY`
Expected: FAIL

**Step 3: Write minimal implementation**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { host: "0.0.0.0", port: 5173, proxy: { "/api": "http://localhost:8002" } },
});
```

```html
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
```

**Step 4: Run test to verify it passes**

Run: `python - <<'PY'
import os
assert os.path.exists("frontend/vite.config.ts")
PY`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/index.html frontend/src/main.tsx
git commit -m "feat: add vite dev server for frontend"
```

---

### Task 2: Update frontend scripts for dev server

**Files:**
- Modify: `frontend/package.json`

**Step 1: Write the failing test**

```python
import json
with open("frontend/package.json") as handle:
    pkg = json.load(handle)
assert "dev" in pkg.get("scripts", {})
```

**Step 2: Run test to verify it fails**

Run: `python - <<'PY'
import json
with open("frontend/package.json") as handle:
    pkg = json.load(handle)
assert "dev" in pkg.get("scripts", {})
PY`
Expected: FAIL

**Step 3: Write minimal implementation**

```json
"scripts": {
  "dev": "vite",
  "test": "jest",
  "build": "vite build",
  "preview": "vite preview"
}
```

**Step 4: Run test to verify it passes**

Run: `python - <<'PY'
import json
with open("frontend/package.json") as handle:
    pkg = json.load(handle)
assert "dev" in pkg.get("scripts", {})
PY`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/package.json
git commit -m "chore: add frontend dev scripts"
```

---

**Plan complete and saved to `docs/plans/2026-03-15-week8-vite-preview-implementation-plan.md`.** Two execution options:

**1. Subagent-Driven (this session)** – I dispatch fresh subagent per task, review between tasks, fast iteration  
**2. Parallel Session (separate)** – Open new session with executing-plans, batch execution with checkpoints

Which approach?
