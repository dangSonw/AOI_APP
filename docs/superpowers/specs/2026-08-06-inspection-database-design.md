# Inspection Database Design Specification

**Date:** 2026-08-06  
**Author:** AI Agent  
**Status:** Approved for implementation  
**Scope:** Full inspection persistence layer – PostgreSQL schema, backend API, frontend Database tab

---

## 1. Overview

The AOI system requires a complete inspection database to persist board inspection results, defect records, and captured image metadata. PostgreSQL stores structured metadata and references; large image artifacts remain on disk as files. The database column for images stores only a **relative path** to the image file – no binary data or compressed blobs.

## 2. Tables

### users (existing)
Authentication table. Already implemented.

### recipes
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PK | Auto-increment ID |
| slug | VARCHAR(128) | UNIQUE NOT NULL | URL-safe identifier |
| name | VARCHAR(255) | NOT NULL | Human-readable name |
| description | TEXT | DEFAULT '' | Optional description |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | Soft-delete flag |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW | Created |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW | Updated |

### inspection_results
One row per inspected board.
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PK | ID |
| board_serial | VARCHAR(128) | NOT NULL | e.g. PCB-24-08192 |
| lot | VARCHAR(128) | DEFAULT '' | Manufacturing lot |
| recipe_id | BIGINT | FK recipes.id NOT NULL | Recipe used |
| recipe_name | VARCHAR(255) | NOT NULL | Recipe name snapshot |
| operator_id | BIGINT | FK users.id NOT NULL | Operator |
| result | VARCHAR(10) | NOT NULL CHECK(PASS/FAIL/REVIEW) | Decision |
| defect_count | INTEGER | DEFAULT 0 | Defects found |
| score | REAL | NULL | Anomaly score 0-1 |
| cycle_time_ms | INTEGER | NULL | Cycle time ms |
| camera_config | JSONB | NULL | Camera config snapshot |
| review_decision | VARCHAR(10) | NULL | Operator override |
| reviewed_by | BIGINT | FK users.id NULL | Reviewer |
| reviewed_at | TIMESTAMPTZ | NULL | Review time |
| inspected_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW | Inspection time |

### defects
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PK | ID |
| result_id | BIGINT | FK inspection_results.id NOT NULL | Parent |
| defect_type | VARCHAR(64) | NOT NULL | e.g. missing_component |
| severity | VARCHAR(20) | DEFAULT 'medium' | low/medium/high/critical |
| location_x | REAL | NULL | X px on board |
| location_y | REAL | NULL | Y px on board |
| width | REAL | NULL | Bbox width px |
| height | REAL | NULL | Bbox height px |
| confidence | REAL | NULL | Confidence 0-1 |
| description | TEXT | DEFAULT '' | Optional |
| detected_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW | Detected |

### inspection_images
Images are NEVER stored as blobs. Only relative paths.
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PK | ID |
| result_id | BIGINT | FK inspection_results.id NOT NULL | Parent |
| defect_id | BIGINT | FK defects.id NULL | Optional defect link |
| image_type | VARCHAR(32) | NOT NULL | original/annotated/evidence/thumbnail |
| relative_path | VARCHAR(512) | NOT NULL | Path from project root |
| file_size_bytes | BIGINT | NULL | Size bytes |
| width_px | INTEGER | NULL | Width px |
| height_px | INTEGER | NULL | Height px |
| sha256_hash | VARCHAR(64) | NULL | Integrity check |
| media_type | VARCHAR(64) | DEFAULT 'image/png' | MIME type |
| captured_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW | Captured |

## 3. Image Storage

- Stored under `data/captures/{YYYY}/{MM}/{DD}/{board_serial}/`
- `inspection_images.relative_path` = path relative to project root
- Example: `data/captures/2026/08/06/PCB-24-08192/original.png`
- SHA-256 checksum stored for integrity verification

## 4. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/inspections | List with filter & pagination |
| GET | /api/inspections/{id} | Detail with defects & images |
| GET | /api/inspections/metrics | Dashboard metrics |
| POST | /api/inspections | Create result |
| PATCH | /api/inspections/{id}/review | Submit review |
| GET | /api/inspections/export | CSV export |
| GET | /api/recipes | List recipes |
| POST | /api/recipes | Create recipe |

## 5. Query Params for GET /api/inspections

page, page_size, result, recipe_slug, lot, search, date_from, date_to, sort_by, sort_order

## 6. Frontend Database Tab

- Header: title, search, filters
- Metrics: total, yield%, flagged, storage
- Two-column: records table (left) + detail panel (right)
- Pagination, CSV export, review action
