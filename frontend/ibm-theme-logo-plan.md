# Frontend IBM theme and logo plan

## Top-Level Overview

Update the frontend branding with the minimal scope requested. The PrimeVue primary theme color will be changed to IBM brand blue `#0530AD` while preserving all other semantic colors. On the home toolbar, the existing action buttons will shift right to make room for a small IBM logo at the far left as a standalone image, not a button.

## Sub-Tasks

### 1. Update the frontend primary theme color
- **Intent** — Align the site's primary interactive color with the IBM Design Language brand blue without changing unrelated semantic tokens.
- **Expected Outcomes** — Primary-styled PrimeVue controls use IBM blue `#0530AD`; success, warning, and danger colors remain unchanged.
- **Todo List**
  1. Review the existing PrimeVue theme setup in [`frontend/src/main.ts`](frontend/src/main.ts).
  2. Apply the smallest supported PrimeVue theme override for the primary color token only.
  3. Confirm no unrelated color tokens are modified.
- **Relevant Context** — [`frontend/src/main.ts`](frontend/src/main.ts)
- **Status** — [x] done

### 2. Add the IBM logo to the far left of the home toolbar
- **Intent** — Make space at the left edge of the toolbar and place the IBM logo there as a small standalone brand mark, while leaving the existing buttons functionally unchanged.
- **Expected Outcomes** — The home toolbar in [`frontend/src/views/HomeView.vue`](frontend/src/views/HomeView.vue) shows the IBM logo on the far left, followed by the existing buttons shifted right.
- **Todo List**
  1. Update the toolbar markup in [`frontend/src/views/HomeView.vue`](frontend/src/views/HomeView.vue) to add the logo image before the buttons.
  2. Add only the CSS needed to size and align the logo with the toolbar layout.
  3. Keep the logo as an image element rather than a button and avoid broader style changes.
- **Relevant Context** — [`frontend/src/views/HomeView.vue`](frontend/src/views/HomeView.vue), [`frontend/IBM_core_gray60_on_white.svg`](frontend/IBM_core_gray60_on_white.svg)
- **Status** — [x] done

### 3. Validate the frontend build
- **Intent** — Verify the branding changes compile cleanly in the existing frontend build pipeline.
- **Expected Outcomes** — [`npm run build`](frontend/package.json) completes successfully with the updated frontend.
- **Todo List**
  1. Run the existing frontend build command from [`frontend/package.json`](frontend/package.json).
  2. Review the output for new type or build issues related to the branding changes.
- **Relevant Context** — [`frontend/package.json`](frontend/package.json)
- **Status** — [ ] pending
