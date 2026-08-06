# Inspection Database Implementation Plan

**Date:** 2026-08-06  
**Spec:** `specs/2026-08-06-inspection-database-design.md`  
**Goal:** Deliver full inspection persistence: PostgreSQL schema, backend models/services/API, frontend DatabasePage, tests, scripts.

---

## Phase 1: Database Schema & Scripts

### Task 1.1: Create SQL schema files in `database/schema/`
- `002_create_recipes.sql`
- `003_create_inspection_results.sql`
- `004_create_defects.sql`
- `005_create_inspection_images.sql`

### Task 1.2: Create query files in `database/queries/`
- `get_inspection_metrics.sql` – aggregate stats
- `list_inspections.sql` – paginated listing with filters
- `search_inspections.sql` – full-text search
- `get_inspection_detail.sql` – single result + defects + images

### Task 1.3: Create seed data in `database/seed/`
- `seed_recipes.sql` – sample recipes
- `seed_sample_inspections.sql` – sample inspection data

### Task 1.4: Create database scripts
- `database/scripts/reset_database.sql` – DROP + recreate all tables
- Update `scripts/install/setup-postgresql.sh` to run all schema files

## Phase 2: Backend Models

### Task 2.1: SQLAlchemy models in `backend/app/models/`
- `recipe.py` – Recipe model
- `inspection_result.py` – InspectionResult model
- `defect.py` – Defect model
- `inspection_image.py` – InspectionImage model

### Task 2.2: Update `bootstrap.py`
- Import all new models so `Base.metadata.create_all()` creates them
- Seed default recipes

## Phase 3: Backend Schemas & Services

### Task 3.1: Pydantic schemas in `backend/app/schemas/`
- `inspection.py` – request/response schemas for inspections
- `recipe.py` – request/response schemas for recipes

### Task 3.2: Service layer in `backend/app/services/`
- `inspection_service.py` – CRUD + filtering + metrics
- `recipe_service.py` – recipe CRUD

## Phase 4: Backend API

### Task 4.1: API routes in `backend/app/api/`
- `inspections.py` – all inspection endpoints
- `recipes.py` – recipe endpoints

### Task 4.2: Register routers in `main.py`

## Phase 5: Frontend

### Task 5.1: Types in `frontend/src/types/`
- `inspection.ts` – TypeScript interfaces

### Task 5.2: Service in `frontend/src/services/`
- `inspection-service.ts` – API client functions

### Task 5.3: Rewrite `DatabasePage.tsx`
- Replace hardcoded mock data with real API calls
- Add pagination, filtering, metrics from backend
- Keep existing CSS classes and layout structure

### Task 5.4: Update `WorkspacePage.tsx`
- Pass accessToken to DatabasePage

## Phase 6: Tests & Verification

### Task 6.1: Backend tests
- Service tests for inspection_service
- API integration tests

### Task 6.2: Final verification
- Run existing test suite to ensure no regressions
