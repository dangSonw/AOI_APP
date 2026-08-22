"""Dataset API router."""

from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from app.auth.dependencies import CurrentUser
from app.schemas.dataset import (
    CaptureListResponse,
    CategoryCreateRequest,
    CategoryRenameRequest,
    DatasetCreateRequest,
    DatasetDetail,
    DatasetListResponse,
    DatasetValidationReport,
    CsvPreviewResponse,
    CsvPreparationResponse,
    CsvPreparationSnapshotResponse,
    CsvPreprocessingPreviewResponse,
    CsvProcessedArtifactResponse,
    CsvProcessedArtifactListResponse,
    CsvProcessedArtifactVerificationResponse,
    CsvKnnTrainingJobListResponse,
    CsvKnnTrainingJobResponse,
    CsvKnnTrainingRequest,
    DatasetUpdateRequest,
    ImageListResponse,
    ImageMoveRequest,
    ImageRenameRequest,
    ImportCapturesRequest,
)
from app.services import dataset_service

router = APIRouter(prefix='/api/datasets', tags=['datasets'])


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    raise exc


# ---------------------------------------------------------------------------
# Captures endpoint (must be declared before /{name} wildcard routes)
# ---------------------------------------------------------------------------


@router.get('/captures/available', response_model=CaptureListResponse)
def list_captures(_: CurrentUser) -> dict:
    files = dataset_service.list_captures()
    return {'files': files}


# ---------------------------------------------------------------------------
# Dataset CRUD
# ---------------------------------------------------------------------------


@router.get('', response_model=DatasetListResponse)
def list_datasets(_: CurrentUser) -> dict:
    datasets = dataset_service.list_datasets()
    return {'datasets': datasets}


@router.post('', response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
def create_dataset(request: DatasetCreateRequest, _: CurrentUser) -> dict:
    try:
        return dataset_service.create_dataset(
            name=request.name,
            description=request.description,
        )
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.get('/{name}', response_model=DatasetDetail)
def get_dataset(name: str, _: CurrentUser) -> dict:
    try:
        return dataset_service.get_dataset(name)
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/validate', response_model=DatasetValidationReport)
def validate_dataset(name: str, _: CurrentUser) -> dict:
    try:
        return dataset_service.validate_dataset(name)
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/csv-preview', response_model=CsvPreviewResponse)
async def preview_csv(name: str, _: CurrentUser, file: UploadFile = File(...)) -> dict:
    del name
    try:
        content = await file.read()
        return dataset_service.preview_csv(file.filename or 'upload.csv', content)
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/csv-prepare', response_model=CsvPreparationResponse)
async def prepare_csv(
    name: str,
    _: CurrentUser,
    file: UploadFile = File(...),
    target_column: str = Form(...),
    feature_columns: str = Form(...),
    train_ratio: float = Form(0.7),
    validation_ratio: float = Form(0.15),
    test_ratio: float = Form(0.15),
) -> dict:
    del name
    try:
        parsed_features = json.loads(feature_columns)
        if not isinstance(parsed_features, list) or not all(isinstance(item, str) for item in parsed_features):
            raise ValueError('Feature columns must be a JSON array of strings.')
        content = await file.read()
        return dataset_service.prepare_csv(
            file.filename or 'upload.csv',
            content,
            target_column=target_column,
            feature_columns=parsed_features,
            train_ratio=train_ratio,
            validation_ratio=validation_ratio,
            test_ratio=test_ratio,
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Feature columns must be valid JSON.') from exc
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/csv-preparations', response_model=CsvPreparationSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_csv_preparation_snapshot(
    name: str,
    _: CurrentUser,
    file: UploadFile = File(...),
    target_column: str = Form(...),
    feature_columns: str = Form(...),
    train_ratio: float = Form(0.7),
    validation_ratio: float = Form(0.15),
    test_ratio: float = Form(0.15),
    preprocessing_policy: str = Form('{}'),
) -> dict:
    try:
        parsed_features = json.loads(feature_columns)
        if not isinstance(parsed_features, list) or not all(isinstance(item, str) for item in parsed_features):
            raise ValueError('Feature columns must be a JSON array of strings.')
        content = await file.read()
        parsed_policy = json.loads(preprocessing_policy)
        if not isinstance(parsed_policy, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in parsed_policy.items()):
            raise ValueError('Preprocessing policy must be a JSON object of string values.')
        return dataset_service.create_csv_preparation_snapshot(
            name,
            file.filename or 'upload.csv',
            content,
            target_column=target_column,
            feature_columns=parsed_features,
            train_ratio=train_ratio,
            validation_ratio=validation_ratio,
            test_ratio=test_ratio,
            preprocessing_policy=parsed_policy,
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Feature columns must be valid JSON.') from exc
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/csv-preparations/{preparation_id}/preview', response_model=CsvPreprocessingPreviewResponse)
def preview_csv_preprocessing(name: str, preparation_id: str, _: CurrentUser) -> dict:
    try:
        return dataset_service.preview_csv_preprocessing(name, preparation_id)
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/csv-preparations/{preparation_id}/artifacts', response_model=CsvProcessedArtifactResponse, status_code=status.HTTP_201_CREATED)
def create_csv_processed_artifact(name: str, preparation_id: str, _: CurrentUser) -> dict:
    try:
        return dataset_service.create_csv_processed_artifact(name, preparation_id)
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.get('/{name}/csv-preparations/{preparation_id}/artifacts', response_model=CsvProcessedArtifactListResponse)
def list_csv_processed_artifacts(name: str, preparation_id: str, _: CurrentUser) -> dict:
    try:
        return {'artifacts': dataset_service.list_csv_processed_artifacts(name, preparation_id)}
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/csv-preparations/{preparation_id}/artifacts/{artifact_id}/verify', response_model=CsvProcessedArtifactVerificationResponse)
def verify_csv_processed_artifact(name: str, preparation_id: str, artifact_id: str, _: CurrentUser) -> dict:
    try:
        return dataset_service.verify_csv_processed_artifact(name, preparation_id, artifact_id)
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/csv-preparations/{preparation_id}/artifacts/{artifact_id}/knn-jobs', response_model=CsvKnnTrainingJobResponse, status_code=status.HTTP_201_CREATED)
def create_csv_knn_training_job(name: str, preparation_id: str, artifact_id: str, request: CsvKnnTrainingRequest, _: CurrentUser) -> dict:
    try:
        return dataset_service.create_csv_knn_training_job(name, preparation_id, artifact_id, request.k)
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.get('/{name}/csv-preparations/{preparation_id}/artifacts/{artifact_id}/knn-jobs', response_model=CsvKnnTrainingJobListResponse)
def list_csv_knn_training_jobs(name: str, preparation_id: str, artifact_id: str, _: CurrentUser) -> dict:
    try:
        return {'jobs': dataset_service.list_csv_knn_training_jobs(name, preparation_id, artifact_id)}
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.put('/{name}', response_model=DatasetDetail)
def update_dataset(
    name: str,
    request: DatasetUpdateRequest,
    _: CurrentUser,
) -> dict:
    try:
        return dataset_service.update_dataset(
            name=name,
            new_name=request.new_name,
            description=request.description,
        )
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.delete('/{name}', status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_dataset(name: str, _: CurrentUser) -> None:
    try:
        dataset_service.delete_dataset(name)
    except Exception as exc:
        _handle_error(exc)
        raise exc



# ---------------------------------------------------------------------------
# Export ZIP & Import Captures
# ---------------------------------------------------------------------------


@router.get('/{name}/export')
def export_dataset(name: str, _: CurrentUser) -> StreamingResponse:
    try:
        zip_buffer = dataset_service.export_dataset_zip(name)
        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={'Content-Disposition': f'attachment; filename="{name}.zip"'},
        )
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/import-captures', response_model=ImageListResponse)
def import_captures(
    name: str,
    request: ImportCapturesRequest,
    _: CurrentUser,
) -> dict:
    try:
        images = dataset_service.import_captures(
            dataset_name=name,
            filenames=request.filenames,
            target_category=request.target_category,
        )
        return {'images': images}
    except Exception as exc:
        _handle_error(exc)
        raise exc


# ---------------------------------------------------------------------------
# Category CRUD
# ---------------------------------------------------------------------------


@router.post('/{name}/categories', response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
def create_category(
    name: str,
    request: CategoryCreateRequest,
    _: CurrentUser,
) -> dict:
    try:
        return dataset_service.create_category(
            dataset_name=name,
            category_name=request.name,
        )
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.put('/{name}/categories/{category_name}', response_model=DatasetDetail)
def rename_category(
    name: str,
    category_name: str,
    request: CategoryRenameRequest,
    _: CurrentUser,
) -> dict:
    try:
        return dataset_service.rename_category(
            dataset_name=name,
            old_name=category_name,
            new_name=request.new_name,
        )
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.delete('/{name}/categories/{category_name}', response_model=DatasetDetail)
def delete_category(
    name: str,
    category_name: str,
    _: CurrentUser,
) -> dict:
    try:
        return dataset_service.delete_category(
            dataset_name=name,
            category_name=category_name,
        )
    except Exception as exc:
        _handle_error(exc)
        raise exc


# ---------------------------------------------------------------------------
# Image Operations
# ---------------------------------------------------------------------------


@router.get('/{name}/categories/{category_name}/images', response_model=ImageListResponse)
def list_images(
    name: str,
    category_name: str,
    _: CurrentUser,
) -> dict:
    try:
        images = dataset_service.list_images(
            dataset_name=name,
            category_name=category_name,
        )
        return {'images': images}
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post(
    '/{name}/categories/{category_name}/images',
    response_model=ImageListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_images(
    name: str,
    category_name: str,
    _: CurrentUser,
    files: list[UploadFile] = File(...),
) -> dict:
    try:
        images = await dataset_service.upload_images(
            dataset_name=name,
            category_name=category_name,
            files=files,
        )
        return {'images': images}
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.get('/{name}/categories/{category_name}/images/{filename}')
def get_image_file(
    name: str,
    category_name: str,
    filename: str,
    _: CurrentUser,
) -> FileResponse:
    try:
        file_path = dataset_service.get_image_path(
            dataset_name=name,
            category_name=category_name,
            filename=filename,
        )
        media_type = dataset_service._media_type_from_extension(filename)
        return FileResponse(file_path, media_type=media_type)
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.delete(
    '/{name}/categories/{category_name}/images/{filename}',
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_image(
    name: str,
    category_name: str,
    filename: str,
    _: CurrentUser,
) -> None:
    try:
        dataset_service.delete_image(
            dataset_name=name,
            category_name=category_name,
            filename=filename,
        )
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.patch('/{name}/categories/{category_name}/images/{filename}')
def rename_image(
    name: str,
    category_name: str,
    filename: str,
    request: ImageRenameRequest,
    _: CurrentUser,
) -> dict:
    try:
        return dataset_service.rename_image(
            dataset_name=name,
            category_name=category_name,
            old_name=filename,
            new_name=request.new_filename,
        )
    except Exception as exc:
        _handle_error(exc)
        raise exc


@router.post('/{name}/categories/{category_name}/images/{filename}/move')
def move_image(
    name: str,
    category_name: str,
    filename: str,
    request: ImageMoveRequest,
    _: CurrentUser,
) -> dict:
    try:
        return dataset_service.move_image(
            dataset_name=name,
            category_name=category_name,
            filename=filename,
            target_category=request.target_category,
        )
    except Exception as exc:
        _handle_error(exc)
        raise exc
