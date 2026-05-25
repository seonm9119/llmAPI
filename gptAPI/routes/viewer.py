import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from client import create_structured_response
from config import GPT_MODEL, VIEWER_ADAPTER_CACHE_PATH, VIEWER_MAX_SCHEMA_CHARS

router = APIRouter(prefix="/viewer")

PROMPT_VERSION = "viewer-mapping-v1"
ADAPTER_CACHE = None

VIEWER_MAPPING_SYSTEM_PROMPT = """
You classify an unknown OCR JSON schema and return a key mapping adapter.
The application already has a deterministic converter. Do not convert OCR rows.
Only identify which source paths map to the fixed viewer schema.

Rules:
- Use only paths visible in the schema fingerprint.
- Use dot paths from the root JSON for image paths, geometry.itemsPath, and parallel array field paths.
- For structure "items", geometry.itemsPath is the root path to annotation items, while geometry.bboxPath, geometry.pointsPath, geometry.xPath, geometry.yPath and fields.*Path are relative to each item.
- For structure "parallel_arrays", geometry.itemsPath is the root path to the geometry array. fields.*Path are root paths to sibling arrays aligned by index.
- If each geometry item is itself [x1, y1, x2, y2], set geometry.bboxPath to "$".
- If each geometry item is itself [[x, y], ...], set geometry.pointsPath to "$".
- For separate x/y arrays inside each item, set geometry.kind to "xy_arrays", geometry.xPath to the x array, and geometry.yPath to the y array.
- For text that embeds tags like <|ref|>...<|det|>[[x1,y1,x2,y2]]<|/det|>, set structure "embedded_text", geometry.kind "det_tag", geometry.format "det", geometry.unit "deepseek_1000", and fields.textPath to the string field.
- Use fields.confidencePath only for confidence, score, probability, or prob paths that represent 0..1 confidence.
- If explicit bbox/polygon/det geometry is not present, return renderMode "unsupported".
""".strip()

VIEWER_MAPPING_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "target",
        "version",
        "renderMode",
        "sourceType",
        "structure",
        "reason",
        "image",
        "geometry",
        "fields",
    ],
    "properties": {
        "target": {"type": "string", "enum": ["ocr_bbox_mapping"]},
        "version": {"type": "integer", "enum": [1]},
        "renderMode": {"type": "string", "enum": ["overlay", "unsupported"]},
        "sourceType": {"type": "string", "enum": ["ocr_result", "unknown"]},
        "structure": {"type": "string", "enum": ["items", "parallel_arrays", "embedded_text", "unsupported"]},
        "reason": {"type": "string"},
        "image": {
            "type": "object",
            "additionalProperties": False,
            "required": ["filenamePath", "widthPath", "heightPath"],
            "properties": {
                "filenamePath": {"type": "string"},
                "widthPath": {"type": "string"},
                "heightPath": {"type": "string"},
            },
        },
        "geometry": {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "itemsPath", "bboxPath", "pointsPath", "xPath", "yPath", "format", "unit"],
            "properties": {
                "kind": {"type": "string", "enum": ["bbox", "polygon", "xy_arrays", "det_tag", "none"]},
                "itemsPath": {"type": "string"},
                "bboxPath": {"type": "string"},
                "pointsPath": {"type": "string"},
                "xPath": {"type": "string"},
                "yPath": {"type": "string"},
                "format": {"type": "string", "enum": ["xyxy", "xywh", "cxcywh", "points", "det", "unknown"]},
                "unit": {"type": "string", "enum": ["pixel", "normalized", "percent", "deepseek_1000", "unknown"]},
            },
        },
        "fields": {
            "type": "object",
            "additionalProperties": False,
            "required": ["idPath", "typePath", "textPath", "confidencePath", "htmlPath"],
            "properties": {
                "idPath": {"type": "string"},
                "typePath": {"type": "string"},
                "textPath": {"type": "string"},
                "confidencePath": {"type": "string"},
                "htmlPath": {"type": "string"},
            },
        },
    },
}


@router.post("/analyze")
async def analyze_viewer_json(request: Request):
    request_data = await request.json()
    sample_json = request_data.get("sample_json")
    schema_summary = request_data.get("schema_summary")

    if sample_json is None and schema_summary is None:
        raise HTTPException(status_code=400, detail="sample_json or schema_summary is required.")

    if schema_summary is None:
        schema_summary = summarize_json_for_viewer(sample_json)

    cache_key = make_cache_key(schema_summary)
    adapter_cache = get_adapter_cache()

    if cache_key in adapter_cache:
        return {
            "success": True,
            "provider": "openai",
            "model": GPT_MODEL,
            "cached": True,
            "cacheType": "disk",
            "adapter": adapter_cache[cache_key],
            "schema_summary": schema_summary,
        }

    user_payload = {
        "task": "Return a viewer mapping adapter for this OCR JSON schema fingerprint.",
        "targetSchema": "ocr_bbox_mapping",
        "schemaFingerprint": trim_schema_summary(schema_summary),
    }

    try:
        mapping, raw_text = create_structured_response(
            VIEWER_MAPPING_SYSTEM_PROMPT,
            user_payload,
            VIEWER_MAPPING_SCHEMA,
            model=GPT_MODEL,
        )
    except Exception as openai_error:
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(openai_error),
                "provider": "openai",
                "model": GPT_MODEL,
            },
        )

    adapter = normalize_viewer_mapping(mapping, sample_json)
    save_adapter_cache_entry(cache_key, adapter)

    return {
        "success": True,
        "provider": "openai",
        "model": GPT_MODEL,
        "cached": False,
        "cacheType": "miss",
        "adapter": adapter,
        "schema_summary": schema_summary,
        "raw_mapping": raw_text,
    }


def get_adapter_cache():
    global ADAPTER_CACHE

    if ADAPTER_CACHE is None:
        ADAPTER_CACHE = load_adapter_cache()

    return ADAPTER_CACHE


def load_adapter_cache():
    cache_path = Path(VIEWER_ADAPTER_CACHE_PATH)

    try:
        if not cache_path.exists():
            return {}

        with cache_path.open("r", encoding="utf-8") as cache_file:
            cache_data = json.load(cache_file)

        if not isinstance(cache_data, dict):
            return {}

        return {
            str(cache_key): adapter
            for cache_key, adapter in cache_data.items()
            if isinstance(adapter, dict)
        }
    except (OSError, json.JSONDecodeError):
        return {}


def save_adapter_cache_entry(cache_key, adapter):
    adapter_cache = get_adapter_cache()
    adapter_cache[cache_key] = adapter
    write_adapter_cache(adapter_cache)


def write_adapter_cache(adapter_cache):
    cache_path = Path(VIEWER_ADAPTER_CACHE_PATH)
    temp_cache_path = cache_path.with_suffix(f"{cache_path.suffix}.tmp")

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        with temp_cache_path.open("w", encoding="utf-8") as cache_file:
            json.dump(adapter_cache, cache_file, ensure_ascii=False, indent=2, sort_keys=True)

        temp_cache_path.replace(cache_path)
    except OSError:
        pass


def make_cache_key(schema_summary):
    cache_payload = {
        "promptVersion": PROMPT_VERSION,
        "model": GPT_MODEL,
        "schemaSummary": schema_summary,
    }
    cache_text = json.dumps(cache_payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(cache_text.encode("utf-8")).hexdigest()


def trim_schema_summary(schema_summary):
    summary_text = json.dumps(schema_summary, ensure_ascii=False)

    if len(summary_text) <= VIEWER_MAX_SCHEMA_CHARS:
        return schema_summary

    return {
        "rootType": schema_summary.get("rootType"),
        "arrayCandidates": (schema_summary.get("arrayCandidates") or [])[:25],
        "parallelArrayGroups": (schema_summary.get("parallelArrayGroups") or [])[:15],
        "scalarCandidates": (schema_summary.get("scalarCandidates") or [])[:60],
        "truncated": True,
    }


def normalize_viewer_mapping(mapping, sample_json):
    if not isinstance(mapping, dict):
        return build_unsupported_mapping("GPT did not return a JSON object.")

    image_mapping = mapping.get("image") if isinstance(mapping.get("image"), dict) else {}
    geometry_mapping = mapping.get("geometry") if isinstance(mapping.get("geometry"), dict) else {}
    fields_mapping = mapping.get("fields") if isinstance(mapping.get("fields"), dict) else {}

    structure = normalize_structure(mapping.get("structure"))
    geometry_items_path = normalize_json_path(geometry_mapping.get("itemsPath") or "")

    adapter = {
        "target": "ocr_bbox_mapping",
        "version": 1,
        "renderMode": normalize_render_mode(mapping.get("renderMode")),
        "sourceType": normalize_source_type(mapping.get("sourceType")),
        "structure": structure,
        "reason": str(mapping.get("reason") or ""),
        "image": {
            "filenamePath": normalize_json_path(image_mapping.get("filenamePath") or ""),
            "widthPath": normalize_json_path(image_mapping.get("widthPath") or ""),
            "heightPath": normalize_json_path(image_mapping.get("heightPath") or ""),
        },
        "geometry": {
            "kind": normalize_geometry_kind(geometry_mapping.get("kind")),
            "itemsPath": geometry_items_path,
            "bboxPath": normalize_mapping_field_path(geometry_mapping.get("bboxPath") or "", structure, geometry_items_path),
            "pointsPath": normalize_mapping_field_path(geometry_mapping.get("pointsPath") or "", structure, geometry_items_path),
            "xPath": normalize_mapping_field_path(geometry_mapping.get("xPath") or "", structure, geometry_items_path),
            "yPath": normalize_mapping_field_path(geometry_mapping.get("yPath") or "", structure, geometry_items_path),
            "format": normalize_geometry_format(geometry_mapping.get("format")),
            "unit": normalize_geometry_unit(geometry_mapping.get("unit")),
        },
        "fields": {
            "idPath": normalize_mapping_field_path(fields_mapping.get("idPath") or "", structure, geometry_items_path),
            "typePath": normalize_mapping_field_path(fields_mapping.get("typePath") or "", structure, geometry_items_path),
            "textPath": normalize_mapping_field_path(fields_mapping.get("textPath") or "", structure, geometry_items_path),
            "confidencePath": normalize_mapping_field_path(fields_mapping.get("confidencePath") or "", structure, geometry_items_path),
            "htmlPath": normalize_mapping_field_path(fields_mapping.get("htmlPath") or "", structure, geometry_items_path),
        },
    }

    repair_mapping(adapter, sample_json)

    if adapter["renderMode"] != "overlay":
        return build_unsupported_mapping(adapter["reason"] or "Adapter render mode is unsupported.")

    if sample_json is not None and not mapping_builds_sample_boxes(adapter, sample_json):
        return build_unsupported_mapping("GPT mapping did not build bbox geometry from the sample JSON.")

    return adapter


def build_unsupported_mapping(reason):
    return {
        "target": "ocr_bbox_mapping",
        "version": 1,
        "renderMode": "unsupported",
        "sourceType": "unknown",
        "structure": "unsupported",
        "reason": reason,
        "image": {
            "filenamePath": "",
            "widthPath": "",
            "heightPath": "",
        },
        "geometry": {
            "kind": "none",
            "itemsPath": "",
            "bboxPath": "",
            "pointsPath": "",
            "xPath": "",
            "yPath": "",
            "format": "unknown",
            "unit": "unknown",
        },
        "fields": {
            "idPath": "",
            "typePath": "",
            "textPath": "",
            "confidencePath": "",
            "htmlPath": "",
        },
    }


def repair_mapping(adapter, sample_json):
    geometry = adapter["geometry"]
    fields = adapter["fields"]

    if geometry["format"] == "unknown":
        if geometry["kind"] == "det_tag":
            geometry["format"] = "det"
        elif geometry["kind"] == "polygon":
            geometry["format"] = "points"
        elif geometry["kind"] in ["bbox", "xy_arrays"]:
            geometry["format"] = "xyxy"

    if geometry["unit"] == "unknown":
        geometry["unit"] = "deepseek_1000" if geometry["kind"] == "det_tag" else "pixel"

    if adapter["structure"] == "embedded_text":
        geometry["kind"] = "det_tag"
        geometry["format"] = "det"
        geometry["unit"] = "deepseek_1000"
        geometry["itemsPath"] = ""

    if sample_json is None:
        return

    repair_indexed_parallel_mapping(adapter, sample_json)

    if adapter["structure"] == "items":
        repair_item_axis_mapping(adapter, sample_json)
    elif adapter["structure"] == "parallel_arrays":
        repair_parallel_mapping(adapter, sample_json)

    if fields["confidencePath"] and not is_confidence_path_name(fields["confidencePath"]):
        fields["confidencePath"] = ""


def repair_item_axis_mapping(adapter, sample_json):
    geometry = adapter["geometry"]
    items = get_json_path_value(sample_json, geometry["itemsPath"])

    if not isinstance(items, list):
        return

    sample_item = next((item for item in items if isinstance(item, dict)), None)

    if sample_item is None:
        return

    if geometry["bboxPath"] and is_axis_coordinate_path(geometry["bboxPath"]):
        axis_paths = find_axis_pair(sample_item, geometry["bboxPath"])

        if axis_paths:
            geometry["kind"] = "xy_arrays"
            geometry["bboxPath"] = ""
            geometry["pointsPath"] = ""
            geometry["xPath"] = axis_paths[0]
            geometry["yPath"] = axis_paths[1]


def repair_indexed_parallel_mapping(adapter, sample_json):
    geometry = adapter["geometry"]
    fields = adapter["fields"]
    parent_path = geometry["itemsPath"]
    parent_value = get_json_path_value(sample_json, parent_path)

    if not isinstance(parent_value, dict):
        return

    geometry_path = geometry["bboxPath"] or geometry["pointsPath"] or ""
    geometry_array_path = strip_trailing_numeric_path_parts(geometry_path)
    geometry_array = get_json_path_value(parent_value, geometry_array_path)

    if not isinstance(geometry_array, list) or not geometry_array:
        return

    first_geometry = get_first_present_value(geometry_array)

    if is_valid_bbox(first_geometry):
        geometry_kind = "bbox"
        bbox_path = "$"
        points_path = ""
        geometry_format = "xyxy"
    elif is_valid_points(first_geometry):
        geometry_kind = "polygon"
        bbox_path = ""
        points_path = "$"
        geometry_format = "points"
    else:
        return

    adapter["structure"] = "parallel_arrays"
    geometry["kind"] = geometry_kind
    geometry["itemsPath"] = join_json_path(parent_path, geometry_array_path)
    geometry["bboxPath"] = bbox_path
    geometry["pointsPath"] = points_path
    geometry["xPath"] = ""
    geometry["yPath"] = ""
    geometry["format"] = geometry_format
    geometry["unit"] = "pixel" if geometry["unit"] == "unknown" else geometry["unit"]

    for field_name, field_path in list(fields.items()):
        if not field_path or field_path == "$":
            continue

        field_array_path = strip_trailing_numeric_path_parts(field_path)
        field_value = get_json_path_value(parent_value, field_array_path)

        if field_value is not None:
            fields[field_name] = join_json_path(parent_path, field_array_path)


def repair_parallel_mapping(adapter, sample_json):
    geometry = adapter["geometry"]
    items = get_json_path_value(sample_json, geometry["itemsPath"])

    if not isinstance(items, list) or not items:
        return

    sample_item = items[0]

    if not geometry["bboxPath"] and not geometry["pointsPath"] and isinstance(sample_item, list):
        if is_valid_bbox(sample_item):
            geometry["kind"] = "bbox"
            geometry["bboxPath"] = "$"
            geometry["format"] = "xyxy" if geometry["format"] == "unknown" else geometry["format"]
        elif is_valid_points(sample_item):
            geometry["kind"] = "polygon"
            geometry["pointsPath"] = "$"
            geometry["format"] = "points"


def normalize_render_mode(render_mode):
    return "overlay" if str(render_mode or "").lower() == "overlay" else "unsupported"


def normalize_source_type(source_type):
    normalized_type = str(source_type or "ocr_result").lower()
    return normalized_type if normalized_type in ["ocr_result", "unknown"] else "ocr_result"


def normalize_structure(structure):
    normalized_structure = str(structure or "").lower()
    return normalized_structure if normalized_structure in ["items", "parallel_arrays", "embedded_text", "unsupported"] else "unsupported"


def normalize_geometry_kind(geometry_kind):
    normalized_kind = str(geometry_kind or "").lower()
    return normalized_kind if normalized_kind in ["bbox", "polygon", "xy_arrays", "det_tag", "none"] else "none"


def normalize_geometry_format(geometry_format):
    normalized_format = str(geometry_format or "").lower()
    return normalized_format if normalized_format in ["xyxy", "xywh", "cxcywh", "points", "det"] else "unknown"


def normalize_geometry_unit(geometry_unit):
    normalized_unit = str(geometry_unit or "").lower()
    return normalized_unit if normalized_unit in ["pixel", "normalized", "percent", "deepseek_1000"] else "unknown"


def normalize_json_path(json_path):
    if not json_path:
        return ""

    normalized_path = str(json_path).strip().removeprefix("$.").replace("[", ".").replace("]", "")

    if normalized_path == "$":
        return "$"

    return ".".join(path_part for path_part in normalized_path.split(".") if path_part)


def normalize_mapping_field_path(field_path, structure, items_path):
    normalized_path = normalize_json_path(field_path)

    if not normalized_path:
        return ""

    if normalized_path == "$":
        return "$"

    if structure == "items" and items_path:
        item_path_prefix = f"{items_path}."

        if normalized_path == items_path:
            return "$"

        if normalized_path.startswith(item_path_prefix):
            normalized_path = normalized_path[len(item_path_prefix):]
            path_parts = normalized_path.split(".")

            while path_parts and path_parts[0].isdigit():
                path_parts = path_parts[1:]

            return ".".join(path_parts)

    return normalized_path


def mapping_builds_sample_boxes(adapter, sample_json):
    structure = adapter["structure"]
    geometry = adapter["geometry"]

    if structure == "embedded_text":
        ocr_text = get_json_path_value(sample_json, adapter["fields"]["textPath"])
        return isinstance(ocr_text, str) and "<|det|>" in ocr_text

    sample_items = get_json_path_value(sample_json, geometry["itemsPath"])

    if not isinstance(sample_items, list) or not sample_items:
        return False

    return any(item_has_geometry(sample_item, geometry) for sample_item in sample_items[:5])


def item_has_geometry(sample_item, geometry):
    if geometry["kind"] == "xy_arrays":
        return is_valid_axis_coordinates(
            get_json_path_value(sample_item, geometry["xPath"]),
            get_json_path_value(sample_item, geometry["yPath"]),
        )

    if geometry["bboxPath"]:
        return is_valid_bbox(get_json_path_value(sample_item, geometry["bboxPath"]))

    if geometry["pointsPath"]:
        return is_valid_points(get_json_path_value(sample_item, geometry["pointsPath"]))

    return False


def get_json_path_value(json_value, json_path):
    normalized_path = normalize_json_path(json_path)

    if not normalized_path:
        return None

    if normalized_path == "$":
        return json_value

    current_value = json_value

    for path_part in normalized_path.split("."):
        if isinstance(current_value, dict):
            current_value = current_value.get(path_part)
        elif isinstance(current_value, list) and path_part.isdigit():
            item_index = int(path_part)
            current_value = current_value[item_index] if item_index < len(current_value) else None
        else:
            return None

        if current_value is None:
            return None

    return current_value


def join_json_path(parent_path, child_path):
    normalized_parent = normalize_json_path(parent_path)
    normalized_child = normalize_json_path(child_path)

    if not normalized_parent or normalized_parent == "$":
        return normalized_child

    if not normalized_child or normalized_child == "$":
        return normalized_parent

    return f"{normalized_parent}.{normalized_child}"


def strip_trailing_numeric_path_parts(json_path):
    path_parts = normalize_json_path(json_path).split(".")

    while path_parts and path_parts[-1].isdigit():
        path_parts = path_parts[:-1]

    return ".".join(path_parts)


def is_valid_bbox(raw_bbox):
    if isinstance(raw_bbox, list) and len(raw_bbox) == 4:
        return all(is_number(coordinate) for coordinate in raw_bbox)

    if isinstance(raw_bbox, dict):
        xyxy_keys = ["x1", "y1", "x2", "y2"]
        xywh_keys = ["x", "y", "width", "height"]
        return all(is_number(raw_bbox.get(key)) for key in xyxy_keys) or all(is_number(raw_bbox.get(key)) for key in xywh_keys)

    return False


def is_valid_points(raw_points):
    if not isinstance(raw_points, list) or len(raw_points) < 2:
        return False

    valid_points = [
        point
        for point in raw_points
        if isinstance(point, list) and len(point) >= 2 and is_number(point[0]) and is_number(point[1])
    ]
    return len(valid_points) >= 2


def is_valid_axis_coordinates(x_coordinates, y_coordinates):
    if not isinstance(x_coordinates, list) or not isinstance(y_coordinates, list):
        return False

    if len(x_coordinates) < 2 or len(y_coordinates) < 2:
        return False

    return all(is_number(coordinate) for coordinate in x_coordinates[:4]) and all(is_number(coordinate) for coordinate in y_coordinates[:4])


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_confidence_path_name(json_path):
    path_name = get_last_path_part(json_path)
    confidence_names = {
        "confidence",
        "conf",
        "score",
        "scores",
        "prob",
        "probs",
        "probability",
        "probabilities",
    }
    return path_name in confidence_names or any(token in path_name for token in ["confidence", "score", "prob"])


def find_axis_pair(sample_item, axis_path):
    normalized_axis_path = normalize_json_path(axis_path)
    path_parts = normalized_axis_path.split(".") if normalized_axis_path else []

    while path_parts and path_parts[-1].isdigit():
        path_parts = path_parts[:-1]

    axis_path = ".".join(path_parts)
    axis_name = get_last_path_part(axis_path)
    sibling_name = get_matching_y_axis_name(axis_name) if is_x_axis_path(axis_path) else get_matching_x_axis_name(axis_name)

    if not sibling_name:
        return None

    sibling_path_parts = axis_path.split(".")
    sibling_path_parts[-1] = sibling_name
    sibling_path = ".".join(sibling_path_parts)

    if is_valid_axis_coordinates(get_json_path_value(sample_item, axis_path), get_json_path_value(sample_item, sibling_path)):
        if is_x_axis_path(axis_path):
            return axis_path, sibling_path

        return sibling_path, axis_path

    return None


def get_last_path_part(json_path):
    return (normalize_json_path(json_path).split(".")[-1] if json_path else "").lower()


def is_axis_coordinate_path(json_path):
    return is_x_axis_path(json_path) or is_y_axis_path(json_path)


def is_x_axis_path(json_path):
    return get_last_path_part(json_path) in {
        "x",
        "xs",
        "x_points",
        "xcoordinates",
        "x_coordinates",
        "xcoordinate",
        "x_coordinate",
    }


def is_y_axis_path(json_path):
    return get_last_path_part(json_path) in {
        "y",
        "ys",
        "y_points",
        "ycoordinates",
        "y_coordinates",
        "ycoordinate",
        "y_coordinate",
    }


def get_matching_y_axis_name(path_part):
    axis_name_pairs = {
        "x": "y",
        "xs": "ys",
        "x_points": "y_points",
        "xcoordinates": "ycoordinates",
        "x_coordinates": "y_coordinates",
        "xcoordinate": "ycoordinate",
        "x_coordinate": "y_coordinate",
    }
    return axis_name_pairs.get(str(path_part or "").lower(), "")


def get_matching_x_axis_name(path_part):
    axis_name_pairs = {
        "y": "x",
        "ys": "xs",
        "y_points": "x_points",
        "ycoordinates": "xcoordinates",
        "y_coordinates": "x_coordinates",
        "ycoordinate": "xcoordinate",
        "y_coordinate": "x_coordinate",
    }
    return axis_name_pairs.get(str(path_part or "").lower(), "")


def summarize_json_for_viewer(sample_json):
    return {
        "rootType": get_json_kind(sample_json),
        "structure": summarize_json_value(sample_json, 0),
        "arrayCandidates": collect_array_candidates(sample_json),
        "parallelArrayGroups": collect_parallel_array_groups(sample_json),
        "scalarCandidates": collect_scalar_candidates(sample_json),
    }


def summarize_json_value(json_value, depth):
    if depth >= 5:
        return {"type": get_json_kind(json_value)}

    if isinstance(json_value, dict):
        return {
            "type": "object",
            "keys": {
                key: summarize_json_value(child_value, depth + 1)
                for key, child_value in list(json_value.items())[:40]
            },
        }

    if isinstance(json_value, list):
        return {
            "type": "array",
            "length": len(json_value),
            "shape": get_array_shape(json_value),
            "item": summarize_json_value(get_first_present_value(json_value), depth + 1) if json_value else {"type": "null"},
        }

    if isinstance(json_value, str):
        return {"type": "string", "length": len(json_value), "detTag": "<|det|>" in json_value}

    return {"type": get_json_kind(json_value)}


def collect_array_candidates(sample_json):
    array_candidates = []
    collect_array_candidate_paths(sample_json, "", array_candidates)
    return array_candidates[:40]


def collect_array_candidate_paths(json_value, path, array_candidates):
    if isinstance(json_value, list):
        array_candidates.append(summarize_array_candidate(json_value, path))

        for index, child_value in enumerate(json_value[:2]):
            child_path = f"{path}.{index}" if path else str(index)
            collect_array_candidate_paths(child_value, child_path, array_candidates)
        return

    if isinstance(json_value, dict):
        for key, child_value in json_value.items():
            child_path = f"{path}.{key}" if path else key
            collect_array_candidate_paths(child_value, child_path, array_candidates)


def summarize_array_candidate(array_value, path):
    candidate = {
        "path": path or "$",
        "length": len(array_value),
        "shape": get_array_shape(array_value),
        "roleHints": get_path_role_hints(path),
    }
    first_value = get_first_present_value(array_value)

    if isinstance(first_value, dict):
        candidate["itemType"] = "object"
        candidate["itemKeys"] = list(first_value.keys())[:30]
    elif isinstance(first_value, list):
        candidate["itemType"] = "array"
        candidate["itemShape"] = summarize_json_value(first_value, 0)
        candidate["numericRange"] = get_nested_numeric_range(array_value)
    else:
        candidate["itemType"] = get_json_kind(first_value)

        if is_string_array(array_value):
            candidate["stringLengthRange"] = get_string_length_range(array_value)
        elif is_numeric_array(array_value):
            candidate["numericRange"] = get_numeric_range(array_value)

    return candidate


def collect_parallel_array_groups(sample_json):
    parallel_groups = []
    collect_parallel_array_group_paths(sample_json, "", parallel_groups)
    return parallel_groups[:20]


def collect_parallel_array_group_paths(json_value, path, parallel_groups):
    if isinstance(json_value, dict):
        list_children = [
            (key, child_value)
            for key, child_value in json_value.items()
            if isinstance(child_value, list) and child_value
        ]
        length_groups = {}

        for key, child_value in list_children:
            length_groups.setdefault(len(child_value), []).append((key, child_value))

        for group_length, group_children in length_groups.items():
            if len(group_children) < 2:
                continue

            parallel_groups.append({
                "parentPath": path or "$",
                "length": group_length,
                "arrays": [
                    {
                        "path": f"{path}.{key}" if path else key,
                        "shape": get_array_shape(child_value),
                        "roleHints": get_path_role_hints(key),
                    }
                    for key, child_value in group_children[:12]
                ],
            })

        for key, child_value in json_value.items():
            child_path = f"{path}.{key}" if path else key
            collect_parallel_array_group_paths(child_value, child_path, parallel_groups)
        return

    if isinstance(json_value, list):
        for index, child_value in enumerate(json_value[:2]):
            child_path = f"{path}.{index}" if path else str(index)
            collect_parallel_array_group_paths(child_value, child_path, parallel_groups)


def collect_scalar_candidates(sample_json):
    scalar_candidates = []
    collect_scalar_candidate_paths(sample_json, "", scalar_candidates)
    return scalar_candidates[:80]


def collect_scalar_candidate_paths(json_value, path, scalar_candidates):
    if isinstance(json_value, bool):
        return

    if isinstance(json_value, (int, float, str)) or json_value is None:
        role_hints = get_path_role_hints(path)

        if role_hints or get_json_kind(json_value) in ["number", "string"]:
            scalar_candidates.append({
                "path": path or "$",
                "type": get_json_kind(json_value),
                "roleHints": role_hints,
                "detTag": isinstance(json_value, str) and "<|det|>" in json_value,
            })
        return

    if isinstance(json_value, dict):
        for key, child_value in json_value.items():
            child_path = f"{path}.{key}" if path else key
            collect_scalar_candidate_paths(child_value, child_path, scalar_candidates)
        return

    if isinstance(json_value, list):
        for index, child_value in enumerate(json_value[:2]):
            if isinstance(child_value, dict):
                child_path = f"{path}.{index}" if path else str(index)
                collect_scalar_candidate_paths(child_value, child_path, scalar_candidates)


def get_array_shape(array_value):
    if is_numeric_array(array_value):
        return "numeric_array"

    if is_string_array(array_value):
        return "string_array"

    if is_list_of_numeric_vectors(array_value):
        return "numeric_vectors"

    if is_list_of_point_arrays(array_value):
        return "point_arrays"

    first_value = get_first_present_value(array_value)

    if isinstance(first_value, dict):
        return "objects"

    if isinstance(first_value, list):
        return "nested_arrays"

    return get_json_kind(first_value)


def is_numeric_array(array_value):
    return isinstance(array_value, list) and bool(array_value) and all(is_number(child_value) for child_value in array_value)


def is_string_array(array_value):
    return isinstance(array_value, list) and bool(array_value) and all(isinstance(child_value, str) for child_value in array_value)


def is_list_of_numeric_vectors(array_value):
    return (
        isinstance(array_value, list)
        and bool(array_value)
        and all(is_numeric_array(child_value) for child_value in array_value[:5])
    )


def is_list_of_point_arrays(array_value):
    return (
        isinstance(array_value, list)
        and bool(array_value)
        and all(isinstance(child_value, list) and is_list_of_numeric_vectors(child_value) for child_value in array_value[:3])
    )


def get_first_present_value(array_value):
    if not isinstance(array_value, list):
        return None

    for child_value in array_value:
        if child_value is not None:
            return child_value

    return None


def get_numeric_range(array_value):
    numeric_values = [child_value for child_value in array_value if is_number(child_value)]

    if not numeric_values:
        return None

    return {"min": min(numeric_values), "max": max(numeric_values)}


def get_nested_numeric_range(json_value):
    numeric_values = []
    collect_nested_numeric_values(json_value, numeric_values)

    if not numeric_values:
        return None

    return {"min": min(numeric_values), "max": max(numeric_values)}


def collect_nested_numeric_values(json_value, numeric_values):
    if is_number(json_value):
        numeric_values.append(json_value)
        return

    if isinstance(json_value, list):
        for child_value in json_value[:50]:
            collect_nested_numeric_values(child_value, numeric_values)


def get_string_length_range(array_value):
    string_lengths = [len(child_value) for child_value in array_value if isinstance(child_value, str)]

    if not string_lengths:
        return None

    return {"min": min(string_lengths), "max": max(string_lengths)}


def get_path_role_hints(path):
    normalized_path = str(path or "").lower()
    path_name = normalized_path.split(".")[-1]
    role_hints = []

    if any(token in path_name for token in ["bbox", "box", "boxes", "rec_box", "rec_boxes"]):
        role_hints.append("bbox")

    if any(token in path_name for token in ["poly", "polys", "polygon", "points", "dt_polys", "rec_polys"]):
        role_hints.append("polygon")

    if path_name in ["x", "xs", "x_points", "xcoordinates", "x_coordinates"]:
        role_hints.append("x_axis")

    if path_name in ["y", "ys", "y_points", "ycoordinates", "y_coordinates"]:
        role_hints.append("y_axis")

    if any(token in path_name for token in ["text", "texts", "label", "data", "ocr"]):
        role_hints.append("text")

    if is_confidence_path_name(path_name):
        role_hints.append("confidence")

    if path_name in ["width", "w", "image_width"]:
        role_hints.append("image_width")

    if path_name in ["height", "h", "image_height"]:
        role_hints.append("image_height")

    if any(token in path_name for token in ["filename", "file_name", "identifier", "image", "input_path"]):
        role_hints.append("filename")

    if path_name in ["html", "table_html", "markdown"]:
        role_hints.append("html")

    return role_hints


def get_json_kind(json_value):
    if isinstance(json_value, dict):
        return "object"
    if isinstance(json_value, list):
        return "array"
    if isinstance(json_value, bool):
        return "boolean"
    if isinstance(json_value, (int, float)):
        return "number"
    if json_value is None:
        return "null"
    return "string"
