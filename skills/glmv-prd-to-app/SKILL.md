---
name: glmv-prd-to-app
description: >
  Build a complete, production-ready full-stack web application from PRD documents,
  prototype images, and resource files. Handles the entire pipeline: system design,
  database schema, seed data, backend API, frontend UI, visual verification against
  prototypes, and deployment script generation.

  Use this skill whenever the user:
  - Provides a PRD (product requirement document) and wants a working app built
  - Says things like "根据PRD开发", "build from PRD", "implement this product",
    "把需求文档做成应用", "develop this app from requirements"
  - Has prototype images + requirements and wants full-stack implementation
  - Wants to turn product specifications into a running web application
  - Mentions building an app from wireframes/mockups combined with a requirements doc

  Trigger this skill even if the user just says "帮我开发" or "build this" with PRD
  materials present in the working directory.
---

# GLM-V PRD-to-App: Full-Stack Application Builder

> **Language**: Respond in the same language the user uses. Code comments should match.

Build a complete, deployed web application from PRD + prototypes + resources.
The result must be fully reproducible via a single `bash /workspace/start.sh`.

---

## Phase 0: Material Discovery & Analysis

Before anything else, understand what you're working with.

### 0a. Locate all inputs

```
/workspace/prd.md              ← Product requirement document
/workspace/prototypes/*.jpg    ← UI prototype images (the visual truth)
/workspace/resources/**/*      ← Images, videos, icons, and other assets
```

If the materials are in a different location, adapt accordingly. Read the PRD fully.

### 0b. Deep prototype analysis

For **every** prototype image:

1. **Read each image** using the Read tool — you are multimodal, examine them directly.
2. For each image, document:
   - **Page identity**: which page/view this represents
   - **Layout structure**: header, sidebar, main content, footer, modals
   - **Component inventory**: every button, form, card, table, list, nav element
   - **Content inventory**: all visible text, numbers, labels, placeholder content
   - **Color extraction**: primary, secondary, accent, background, text colors (hex values)
   - **Typography**: font sizes, weights, hierarchy observed
   - **Interactive states**: hover effects, active tabs, selected items, toggles
   - **Data patterns**: what data populates lists/tables/cards — this drives seed data

3. Build a **page map** showing navigation flow between prototype pages.

### 0c. Resource inventory

List all files in `/workspace/resources/` and map each to where it appears in the prototypes.
Every resource file must be used in the final application where relevant.

---

## Phase 1: System Design Document

Produce a comprehensive design document at `/workspace/docs/design.md`.

### 1a. Data Model

For each entity, specify:
- Table/collection name
- All fields with types, constraints, defaults
- Relationships (foreign keys, many-to-many)
- Indexes needed for query patterns
- **Content mapping**: which prototype elements map to which fields

Example:
```
products table:
  id          SERIAL PRIMARY KEY
  name        VARCHAR(200) NOT NULL    ← from product card title
  price       DECIMAL(10,2) NOT NULL   ← from product card price label
  image_url   TEXT NOT NULL             ← from product card image
  category_id INTEGER REFERENCES categories(id) ← from category filter
  ...
```

### 1b. API Design

For every page interaction, define an API endpoint:
- Method + path
- Request params/body schema
- Response schema with example
- Which prototype interaction triggers this API
- Error responses

### 1c. Frontend Architecture

- Component hierarchy (tree structure)
- Route definitions mapping to prototype pages
- State management approach
- How each prototype page maps to components

### 1d. Technology Stack

Choose based on PRD complexity. Recommended defaults:

| Layer | Choice | When to use |
|-------|--------|-------------|
| Frontend | React + TypeScript + Vite | Default for SPAs |
| Frontend | Next.js | If SSR/SEO needed |
| Styling | Tailwind CSS | Default |
| Backend | Node.js + Express | Simple APIs |
| Backend | Python + FastAPI | If PRD mentions Python |
| Database | SQLite | Simple apps, <10 tables |
| Database | PostgreSQL | Complex apps, relationships |
| ORM | Prisma (Node) / SQLAlchemy (Python) | Match backend |

Document the choice and reasoning.

### 1e. Directory Structure

```
/workspace/
├── frontend/          ← or client/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/   ← API client
│   │   ├── types/
│   │   └── assets/     ← copied from /workspace/resources
│   └── ...
├── backend/           ← or server/
│   ├── src/
│   │   ├── routes/
│   │   ├── models/
│   │   ├── controllers/
│   │   ├── middleware/
│   │   └── seed/
│   └── ...
├── docs/
│   ├── design.md
│   └── README.md
├── start.sh
└── prd.md
```

---

## Phase 2: Seed Data Generation

Seed data is critical — it makes the app look real from the first launch.

### Rules

1. **Extract from prototypes**: Every piece of visible text, image, number in the prototype
   images must appear in seed data. Read each prototype image again and transcribe content.

2. **Complete coverage**:
   - Every list/table must have the exact number of items shown in prototypes
   - Every card must have the content matching the prototype
   - Every dropdown must have options matching the prototype
   - Navigation items must match prototype navigation
   - Statistics/counters must match prototype numbers

3. **Use resource files**: Map resource files (images, videos, icons) from
   `/workspace/resources/` to seed data entries. Use relative paths or copy to public/static dir.

4. **No placeholders**: No "Lorem ipsum", no "Test Item 1", no `placeholder.com` images.

5. **Support all states**: Include data that exercises empty states, loaded states,
   error scenarios as specified in the PRD.

### Output

Save seed data as:
- SQL seed files, or
- JSON fixtures, or
- ORM seed scripts

Place in `/workspace/backend/src/seed/` (or equivalent).

---

## Phase 3: Backend Implementation

### 3a. Database schema

- Create migration files for all tables
- Include proper constraints, indexes, foreign keys
- Run migrations to verify they work

### 3b. API endpoints

For each endpoint from the design doc:

1. Implement route handler
2. Add input validation (validate types, required fields, ranges)
3. Add error handling with proper HTTP status codes
4. Test with curl or equivalent to verify response format

### 3c. Seed data loading

- Implement a seed script that:
  - Clears existing data (for idempotent re-seeding)
  - Inserts all seed data in correct dependency order
  - Copies resource files to the correct static serving location
- Verify seed data loads without errors

### 3d. Static file serving

- Configure the backend to serve resource files (images, videos, etc.)
- Ensure frontend can access them via proper URLs

---

## Phase 4: Frontend Implementation

This is where visual fidelity matters most. The prototypes are the **definitive reference**.

### 4a. Global styles and tokens

Before building components, establish:
- Color variables matching prototype colors
- Typography scale matching prototype fonts
- Spacing/sizing system matching prototype spacing
- Common component styles (buttons, cards, inputs, etc.)

### 4b. Page-by-page implementation

For **each prototype image**, in order:

1. **Re-read the prototype image** — keep it fresh in your context
2. Build the page component matching the layout exactly:
   - Match spacing and proportions
   - Match colors and typography
   - Match visual hierarchy
   - Match content placement
3. Wire up API calls to the backend
4. Implement all interactions visible or implied:
   - Navigation between pages
   - Form submissions
   - Search and filter
   - Sorting
   - Modals and dialogs
   - Loading states
   - Error states
   - Hover effects
   - Active/selected states

### 4c. Resource integration

- Copy all resources from `/workspace/resources/` to frontend assets
- Reference them correctly in components
- Ensure images render at proper sizes matching prototypes

### 4d. Responsive considerations

- Match the viewport width shown in prototypes
- If prototypes show mobile views, implement responsive breakpoints

---

## Phase 5: Visual Verification Loop

This phase is what separates a good implementation from a great one.
**Repeat this loop for every page.**

### 5a. Render the page to a screenshot

Use Playwright to capture the running application:

```bash
python ${SKILL_DIR}/scripts/render_page.py \
  --url "http://localhost:3000/page-path" \
  --output "/workspace/docs/screenshots/page_name.png" \
  --width 1280
```

### 5b. Visual comparison

Read both images (prototype and screenshot) side by side:

1. Read the prototype image from `/workspace/prototypes/`
2. Read the rendered screenshot
3. Compare systematically:
   - **Layout**: Are sections in the right positions?
   - **Colors**: Do colors match?
   - **Typography**: Are font sizes/weights correct?
   - **Content**: Is all prototype content present?
   - **Spacing**: Are margins and paddings close?
   - **Images**: Are all images rendering?
   - **Components**: Are all UI components present and correct?

### 5c. Fix discrepancies

For each difference found:
1. Identify the specific CSS/component change needed
2. Apply the fix
3. Re-render and re-compare

### 5d. Repeat until satisfied

Max 3 iterations per page. Focus on the most impactful differences first.

---

## Phase 6: Integration Testing

### 6a. API health check

Run the API health checker to verify all endpoints:

```bash
python ${SKILL_DIR}/scripts/check_api.py \
  --base-url "http://localhost:3000/api" \
  --endpoints-file "/workspace/docs/endpoints.json"
```

Or manually test each endpoint with curl:
```bash
curl -s http://localhost:3000/api/products | head -c 200
```

### 6b. End-to-end flow verification

Walk through every user flow defined in the PRD:
1. Open the app at `http://localhost:3000`
2. Navigate to each page
3. Test each interactive feature
4. Verify data loads from the database
5. Verify forms submit correctly
6. Verify search/filter/sort work

### 6c. Fix any issues found

Address integration issues: CORS, API URL mismatches, data format mismatches, etc.

---

## Phase 7: Deployment Script

Generate `/workspace/start.sh` — the single command that makes everything work from scratch.

### Requirements

The script must:
1. Be fully self-contained — no prior setup assumed
2. Work in a fresh environment
3. Install all system dependencies (Node.js, Python, DB, etc.)
4. Clean any previous state
5. Set up the database from scratch
6. Run all migrations
7. Load all seed data
8. Build the frontend (if needed)
9. Start both backend and frontend
10. Make the app available at `http://localhost:3000`

### Template

```bash
#!/bin/bash
set -e

echo "=== PRD-to-App: Starting deployment ==="

# 1. System dependencies
echo "[1/7] Checking system dependencies..."
# Install Node.js, npm, etc. if missing
# Install database if needed

# 2. Backend setup
echo "[2/7] Setting up backend..."
cd /workspace/backend
npm install  # or pip install -r requirements.txt

# 3. Database initialization
echo "[3/7] Initializing database..."
# Drop existing DB / reset
# Run migrations
# Load seed data

# 4. Frontend setup
echo "[4/7] Setting up frontend..."
cd /workspace/frontend
npm install

# 5. Copy resources
echo "[5/7] Copying resource files..."
# cp -r /workspace/resources/* /workspace/frontend/public/assets/

# 6. Start backend
echo "[6/7] Starting backend server..."
cd /workspace/backend
npm run dev &   # or equivalent
BACKEND_PID=$!

# 7. Start frontend
echo "[7/7] Starting frontend..."
cd /workspace/frontend
PORT=3000 npm run dev &
FRONTEND_PID=$!

echo ""
echo "=== Application is running at http://localhost:3000 ==="
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "To stop: kill $BACKEND_PID $FRONTEND_PID"

wait
```

### Verification

After generating start.sh:
1. `chmod +x /workspace/start.sh`
2. Run it: `bash /workspace/start.sh`
3. Wait for startup
4. Verify `http://localhost:3000` responds
5. Spot-check a few API endpoints
6. Fix any startup issues

---

## Phase 8: Documentation

### 8a. Software Design Document (`/workspace/docs/design.md`)

Already created in Phase 1 — update with any changes made during implementation:
- Final system architecture
- Final data model (with any fields added during dev)
- Technology stack
- Deployment architecture
- API reference

### 8b. README (`/workspace/README.md`)

```markdown
# [Project Name]

## Overview
[From PRD product overview]

## Technology Stack
- Frontend: ...
- Backend: ...
- Database: ...

## Quick Start
\`\`\`bash
bash start.sh
\`\`\`
Then visit http://localhost:3000

## Project Structure
[Directory tree]

## Database
[Schema overview, how to re-seed]

## API Reference
[Key endpoints]
```

---

## Deliverables Checklist

Before declaring done, verify every item:

- [ ] All PRD features implemented — no features skipped
- [ ] All prototype pages built — no pages merged or omitted
- [ ] Visual match with prototypes — verified via screenshot comparison
- [ ] All resource files used where they appear in prototypes
- [ ] Seed data matches prototype content exactly
- [ ] All API endpoints working and returning correct data
- [ ] All interactive elements functional (forms, search, filters, modals, navigation)
- [ ] `bash /workspace/start.sh` works from a clean state
- [ ] App accessible at `http://localhost:3000`
- [ ] Design document complete
- [ ] README with deployment instructions

---

## Critical Principles

1. **Prototypes are truth** — when PRD text and prototype images conflict, the prototype wins
   for visual/layout decisions.

2. **No shortcuts on data** — every piece of content visible in prototypes must come from the
   database via APIs. No hardcoded data in frontend components.

3. **Complete implementation** — every page, every feature, every interaction. Don't skip
   "minor" features. Don't merge separate pages into one.

4. **Resources must be used** — if the prototype shows an image and a matching file exists in
   `/workspace/resources/`, use that file. Don't substitute with placeholder URLs.

5. **Reproducibility** — `start.sh` must work from absolute zero. If it needs Node 18+,
   it installs Node 18+. If it needs PostgreSQL, it sets up PostgreSQL.

6. **Verify, don't assume** — use the visual verification loop (Phase 5) to actually compare
   your output against prototypes. Use API checks to verify endpoints. Run start.sh to verify
   deployment.
