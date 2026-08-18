import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'core' / 'nodes'

ML_GUIDES = {
    'knn-object-classifier': {
        'en': ['Compute the mean BGR vector inside every detection box.', 'Find K closest configured color samples; vote by count or inverse distance.', 'Return the winning label, confidence, and neighbor distances without changing input detections.'],
        'vi': ['Tính vector BGR trung bình bên trong từng bounding box.', 'Tìm K mẫu màu gần nhất; bỏ phiếu theo số lượng hoặc nghịch đảo khoảng cách.', 'Trả nhãn thắng, confidence và khoảng cách láng giềng mà không sửa detection đầu vào.'],
    },
    'knn-image-segmentation': {
        'en': ['Convert every pixel to a normalized BGR query.', 'Find K nearest labeled colors in bounded batches.', 'Set pixels whose winning label is in foregroundLabels to 255, then extract external contours.'],
        'vi': ['Chuyển mỗi pixel thành vector BGR chuẩn hóa.', 'Tìm K mẫu màu có nhãn gần nhất theo từng batch giới hạn.', 'Đặt pixel có nhãn thắng thuộc foregroundLabels thành 255 rồi trích contour ngoài.'],
    },
    'kmeans-image-segmentation': {
        'en': ['Represent pixels in BGR, Lab, or HSV color space.', 'Repeatedly assign pixels to the nearest centroid and update centroid means.', 'Sort learned centroids from darkest ID 0 to brightest ID K-1, then turn foregroundClusters white in the mask.'],
        'vi': ['Biểu diễn pixel trong không gian BGR, Lab hoặc HSV.', 'Lặp bước gán pixel vào centroid gần nhất và cập nhật trung bình centroid.', 'Sắp centroid học được từ ID 0 tối nhất đến ID K-1 sáng nhất, rồi đưa foregroundClusters vào vùng trắng.'],
    },
    'nearest-centroid-object-classifier': {
        'en': ['Compute one mean BGR centroid for each label.', 'Measure each detected object color against every class centroid.', 'Normalize inverse distances into classScores and select the highest score.'],
        'vi': ['Tính một centroid BGR trung bình cho mỗi nhãn.', 'Đo màu trung bình của từng detection với mọi centroid lớp.', 'Chuẩn hóa nghịch đảo khoảng cách thành classScores và chọn điểm cao nhất.'],
    },
    'gaussian-naive-bayes-object-classifier': {
        'en': ['Estimate per-class BGR mean, variance, and prior.', 'Add varianceSmoothing to avoid zero variance.', 'Evaluate Gaussian log posterior and normalize it into class probabilities.'],
        'vi': ['Ước lượng mean, variance BGR và prior cho từng lớp.', 'Cộng varianceSmoothing để tránh variance bằng 0.', 'Tính log-posterior Gaussian rồi chuẩn hóa thành xác suất lớp.'],
    },
    'logistic-object-classifier': {
        'en': ['Standardize object mean-BGR features.', 'Fit linear class weights by scikit-learn or manual softmax gradient descent.', 'Apply softmax to produce classScores; confidence is the winning probability.'],
        'vi': ['Chuẩn hóa feature BGR trung bình của đối tượng.', 'Học trọng số tuyến tính bằng scikit-learn hoặc gradient descent softmax tự viết.', 'Dùng softmax tạo classScores; confidence là xác suất của lớp thắng.'],
    },
    'pca-anomaly-detector': {
        'en': ['Fit a low-dimensional subspace from known-normal BGR samples.', 'Project each pixel into the subspace and reconstruct it.', 'Use normalized reconstruction error as anomaly-map and its configured percentile as score.'],
        'vi': ['Học không gian con ít chiều từ các mẫu BGR normal.', 'Chiếu từng pixel vào không gian con rồi tái tạo.', 'Dùng reconstruction error chuẩn hóa làm anomaly-map và percentile đã chọn làm score.'],
    },
}


def defaults(manifest: dict) -> dict[str, object]:
    return {item['key']: item['default_value'] for item in manifest['definition'].get('parameters', [])}


def workflow(manifest: dict) -> list[str]:
    node_id = manifest['id']
    inputs, outputs = manifest['definition'].get('inputs', []), manifest['definition'].get('outputs', [])
    input_types = {item['data_type'] for item in inputs}
    if {'image', 'detections'} <= input_types:
        return ['image-input', 'global-threshold', 'connected-components', node_id, 'draw-detections']
    result: list[str] = []
    if inputs:
        source = {
            'image': 'image-input', 'mask': 'global-threshold', 'contours': 'find-contours',
            'detections': 'connected-components', 'score': 'mask-coverage-score',
            'boolean': 'logic-not', 'transform': 'estimate-affine-transform',
        }.get(inputs[0]['data_type'])
        if source and source != node_id:
            result.append(source)
    result.append(node_id)
    if outputs:
        target = {
            'image': 'image-output', 'mask': 'overlay-mask', 'contours': 'draw-contours',
            'detections': 'draw-detections', 'score': 'decision-fusion',
            'decision': 'decision-output', 'boolean': 'logic-or',
        }.get(outputs[0]['data_type'])
        if target and target != node_id:
            result.append(target)
    return result


def content(manifest: dict, vi: bool) -> dict:
    definition = manifest['definition']
    node_id, name, description = manifest['id'], definition['name'], definition['description']
    inputs, outputs = definition.get('inputs', []), definition.get('outputs', [])
    reference = definition.get('documentation_reference') or name
    parameter_keys = [parameter['key'] for parameter in definition.get('parameters', [])]
    parameter_process = (
        f"Các parameter {', '.join(f'`{key}`' for key in parameter_keys)} quyết định cách xử lý; thay đổi từng giá trị một để truy vết ảnh hưởng."
        if vi else
        f"Parameters {', '.join(f'`{key}`' for key in parameter_keys)} control processing; change one value at a time to trace its effect."
    ) if parameter_keys else (
        'Node không có parameter; hành vi được quyết định bởi input và contract runtime.' if vi else
        'The node has no parameters; behavior is determined by its input and runtime contract.'
    )
    input_types = ', '.join(f"`{item['key']}`:{item['data_type']}" for item in inputs) or 'none'
    output_types = ', '.join(f"`{item['key']}`:{item['data_type']}" for item in outputs) or 'none'
    if vi:
        overview = f"`{node_id}` thực hiện **{name}** trong pipeline AOI. {description} Người dùng cấu hình node trong Node inspector và nối output sang port cùng kiểu dữ liệu."
        when = f"cần bước {name.lower()} có thể lưu trong recipe, chạy lặp lại và kiểm tra riêng."
        structure = f"Input gồm {input_types}. Node áp dụng {reference}. Output gồm {output_types}. Mỗi key trên sơ đồ chính là tên port phải chọn khi nối dây."
        algorithm = [f"Kiểm tra presence, kiểu dữ liệu và shape của input theo contract `{node_id}`.", parameter_process, f"Áp dụng **{reference}**: {description}", "Chuẩn hóa/đóng gói kết quả theo data type đã khai báo để graph kiểm tra kết nối trước khi chạy."]
        input_guidance = {p['key']: (f"Cấp ảnh `{p['data_type']}`; kiểm tra shape, dtype và thứ tự kênh." if p['data_type'] in {'image', 'mask', 'anomaly-map'} else f"Cấp `{p['data_type']}` đúng semantic của {p['label']}; không dùng dữ liệu ảnh thay thế.") for p in inputs}
        output_guidance = {p['key']: f"{p['label']} kiểu `{p['data_type']}`; xem preview hoặc nối sang node downstream tương thích." for p in outputs}
        parameter_guidance = {p['key']: p.get('description') or f"Nhập `{p['kind']}` trong Min/Max; thử giá trị mặc định trước." for p in definition.get('parameters', [])}
        steps = [f"Kéo **{name}** vào canvas.", "Nối port theo workflow mẫu.", "Mở Node inspector và nhập config JSON bên dưới.", "Bấm Run, xem output rồi chỉ chỉnh một parameter mỗi lần."]
        troubleshooting = [
            {'symptom': 'Không nối được port', 'cause': 'Data type không trùng.', 'resolution': 'Dùng node trung gian tạo đúng kiểu trong bảng port.'},
            {'symptom': 'Invalid parameter', 'cause': 'Ngoài Min/Max hoặc JSON sai.', 'resolution': 'Copy config ví dụ rồi thay từng giá trị.'},
            {'symptom': 'Output rỗng/nhiễu', 'cause': 'Input hoặc tham số không hợp giả định.', 'resolution': 'Preview input, khôi phục mặc định, tinh chỉnh từng bước.'},
        ]
        limitations = ['Node ở trạng thái DEBUG, chưa duyệt production.', f"Kết quả phụ thuộc input và giả định của {reference}.", 'Cần đo latency/bộ nhớ trên phần cứng đích.']
        checklist = ['Khóa camera, ánh sáng, độ phân giải và channel order.', 'Đánh giá tập OK/NG đại diện và đo false-call/escape.', 'Đặt giới hạn parameter, timeout và fail-closed.']
        goal = f"Chạy thử {name.lower()} với input đúng kiểu ({input_types}) và kiểm tra output."
        example_input = f"Dữ liệu cho {input_types}; ảnh dùng uint8 BGR 640×480, các kiểu khác dùng output trực tiếp từ node nguồn trong workflow."
        expected = f"Tạo {', '.join(p['key'] for p in outputs) or 'không có output'} đúng kiểu và không báo lỗi."
    else:
        overview = f"`{node_id}` performs **{name}** in an AOI pipeline. {description} Configure it in Node inspector and connect outputs to ports with matching data types."
        when = f"you need a repeatable {name.lower()} step stored in a recipe and inspectable on its own."
        structure = f"Inputs are {input_types}. The node applies {reference}. Outputs are {output_types}. Each key in the diagram is the exact port name used when connecting edges."
        algorithm = [f"Validate input presence, data types, and shapes against `{node_id}`.", parameter_process, f"Apply **{reference}**: {description}", "Normalize/package results with declared data types so graph compatibility is checked before execution."]
        input_guidance = {p['key']: (f"Provide `{p['data_type']}` image data; verify shape, dtype, and channel order." if p['data_type'] in {'image', 'mask', 'anomaly-map'} else f"Provide `{p['data_type']}` matching {p['label']}; do not substitute image data.") for p in inputs}
        output_guidance = {p['key']: f"{p['label']} as `{p['data_type']}`; preview it or connect a compatible downstream node." for p in outputs}
        parameter_guidance = {p['key']: p.get('description') or f"Enter `{p['kind']}` within Min/Max; try the default first." for p in definition.get('parameters', [])}
        steps = [f"Drag **{name}** onto the canvas.", "Connect ports as shown in the workflow.", "Open Node inspector and enter the JSON config below.", "Run, inspect output, then tune one parameter at a time."]
        troubleshooting = [
            {'symptom': 'Ports cannot connect', 'cause': 'Data types differ.', 'resolution': 'Insert a node producing the exact type in the ports table.'},
            {'symptom': 'Invalid parameter', 'cause': 'Outside Min/Max or malformed JSON.', 'resolution': 'Copy the example config and change one value at a time.'},
            {'symptom': 'Empty/noisy output', 'cause': 'Input or settings violate assumptions.', 'resolution': 'Preview input, restore defaults, and tune incrementally.'},
        ]
        limitations = ['This node is DEBUG and not production-approved.', f"Results depend on input and assumptions of {reference}.", 'Measure latency/memory on target hardware.']
        checklist = ['Lock camera, illumination, resolution, and channel order.', 'Evaluate representative OK/NG data and false-call/escape rates.', 'Set parameter limits, timeouts, and fail-closed checks.']
        goal = f"Run {name.lower()} with correctly typed input ({input_types}) and inspect its output."
        example_input = f"Data for {input_types}; use uint8 BGR 640×480 for images and direct typed output from the shown source node for other types."
        expected = f"Produce {', '.join(p['key'] for p in outputs) or 'no output'} with the declared type and no error."
    special = ML_GUIDES.get(node_id, {}).get('vi' if vi else 'en')
    if special:
        algorithm = [algorithm[0], parameter_process, *special, algorithm[-1]]
        if vi:
            troubleshooting.append({'symptom': 'Hai implementation cho confidence hơi khác', 'cause': 'Solver và tiêu chí dừng khác nhau.', 'resolution': 'So sánh nhãn/metric với tolerance; không yêu cầu số thực giống tuyệt đối.'})
            limitations.append('trainingSamples nằm trong recipe, chỉ phù hợp tập mẫu nhỏ và không chứa dữ liệu nhạy cảm.')
        else:
            troubleshooting.append({'symptom': 'Implementations give slightly different confidence', 'cause': 'Solvers and stopping criteria differ.', 'resolution': 'Compare labels/metrics with tolerance; do not require bit-identical floats.'})
            limitations.append('trainingSamples live in the recipe and are intended only for small, non-sensitive sample sets.')
    return {
        'overview': overview, 'whenToUse': when, 'structure': structure, 'algorithm': algorithm,
        'inputGuidance': input_guidance, 'outputGuidance': output_guidance, 'parameterGuidance': parameter_guidance,
        'example': {'goal': goal, 'workflow': workflow(manifest), 'parameters': defaults(manifest), 'steps': steps, 'input': example_input, 'expectedOutput': expected},
        'troubleshooting': troubleshooting, 'limitations': limitations, 'productionChecklist': checklist,
    }


def main() -> None:
    count = 0
    for path in sorted(ROOT.glob('*/*/manifest.json')):
        manifest = json.loads(path.read_text(encoding='utf-8'))
        if manifest['use'] != 'debug':
            continue
        payload = {'documentationVersion': 1, 'en': content(manifest, False), 'vi': content(manifest, True)}
        with path.with_name('documentation.json').open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
        count += 1
    print(f'Generated documentation metadata for {count} DEBUG nodes.')


if __name__ == '__main__':
    main()