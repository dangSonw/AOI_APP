import json
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.schemas.physical_io import PhysicalInputState, PhysicalOutputState


SchemaType = TypeVar('SchemaType', bound=BaseModel)


class PhysicalIoError(RuntimeError):
    pass


def read_state(file_path: Path, schema: type[SchemaType]) -> SchemaType:
    try:
        with file_path.open('r', encoding='utf-8') as state_file:
            return schema.model_validate(json.load(state_file))
    except FileNotFoundError as error:
        raise PhysicalIoError(f'{file_path.name} is not available.') from error
    except (json.JSONDecodeError, ValidationError) as error:
        raise PhysicalIoError(f'{file_path.name} contains an invalid physical I/O state.') from error


def write_output_state(file_path: Path, state: PhysicalOutputState) -> None:
    temporary_path = file_path.with_suffix('.json.tmp')
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with temporary_path.open('w', encoding='utf-8') as state_file:
            json.dump(state.model_dump(mode='json', by_alias=True), state_file, indent=2)
            state_file.write('\n')
            state_file.flush()
            os.fsync(state_file.fileno())
        temporary_path.replace(file_path)
    except OSError as error:
        temporary_path.unlink(missing_ok=True)
        raise PhysicalIoError('The physical output state could not be written.') from error


def read_input_state(io_directory: Path) -> PhysicalInputState:
    return read_state(io_directory / 'input.json', PhysicalInputState)


def read_output_state(io_directory: Path) -> PhysicalOutputState:
    return read_state(io_directory / 'output.json', PhysicalOutputState)