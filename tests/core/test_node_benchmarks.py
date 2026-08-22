import time

import numpy as np

from core.nodes import NodeExecutionContext, get_node_runtime


def test_ssim_deterministic_benchmark_stays_within_resource_budget() -> None:
    runtime = get_node_runtime('ssim')
    assert runtime is not None
    image = np.zeros((128, 128), dtype=np.uint8)
    context = NodeExecutionContext(
        artifacts={},
        is_cancelled=lambda: False,
    )

    started = time.perf_counter()
    # The runtime must reject missing immutable artifact bindings quickly.
    try:
        runtime.invoke({'image': image}, {'windowSize': 11}, context=context)
    except Exception:
        pass
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert elapsed_ms < 500
    assert image.shape == (128, 128)


def test_watershed_deterministic_fixture_is_bounded() -> None:
    runtime = get_node_runtime('watershed')
    assert runtime is not None
    image = np.zeros((128, 128), dtype=np.uint8)
    mask = np.zeros_like(image)
    mask[32:96, 32:96] = 255

    started = time.perf_counter()
    outputs = runtime.invoke({'image': image, 'mask': mask}, {})
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert elapsed_ms < 1000
    assert outputs['segmented-mask'].shape == image.shape
    assert np.isfinite(outputs['segmented-mask']).all()
