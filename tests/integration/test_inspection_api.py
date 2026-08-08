from datetime import datetime, timezone
from types import SimpleNamespace

from app.api.inspections import build_inspection_detail_response


def test_inspection_detail_response_includes_loaded_evidence() -> None:
    captured_at = datetime(2026, 8, 8, 7, 0, tzinfo=timezone.utc)
    inspection = SimpleNamespace(
        id=42,
        board_serial='PCB-00042',
        lot='LOT-07',
        recipe_name='Rev C · Mainboard',
        recipe=SimpleNamespace(slug='rev-c-mainboard'),
        result='FAIL',
        defect_count=1,
        score=0.91,
        cycle_time_ms=830,
        camera_config={'cameraId': 'top-camera'},
        review_decision=None,
        reviewed_at=None,
        reviewer=None,
        inspected_at=captured_at,
        operator=SimpleNamespace(full_name='AOI Administrator'),
        defects=[SimpleNamespace(
            id=7,
            defect_type='missing-component',
            severity='high',
            location_x=12.5,
            location_y=7.5,
            width=3.0,
            height=2.0,
            confidence=0.98,
            description='U14 is missing.',
            detected_at=captured_at,
        )],
        images=[SimpleNamespace(
            id=9,
            image_type='evidence',
            relative_path='inspection-42/evidence.png',
            file_size_bytes=2048,
            width_px=640,
            height_px=480,
            sha256_hash='a' * 64,
            media_type='image/png',
            defect_id=7,
            captured_at=captured_at,
        )],
    )

    response = build_inspection_detail_response(inspection)
    payload = response.model_dump(mode='json', by_alias=True)

    assert payload['defects'][0]['defectType'] == 'missing-component'
    assert payload['images'][0]['sha256Hash'] == 'a' * 64