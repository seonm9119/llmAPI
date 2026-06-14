import json
import sys

from inference import get_model


def main():
    try:
        request_payload = json.loads(sys.stdin.read() or "{}")
        response_payload = get_model().infer(
            request_payload.get("text"),
            max_new_tokens=request_payload.get("max_new_tokens"),
            temperature=request_payload.get("temperature"),
            include_raw=bool(request_payload.get("include_raw")),
        )
    except ValueError as exc:
        write_error("value_error", str(exc))
        return 2
    except FileNotFoundError as exc:
        write_error("file_not_found", str(exc))
        return 3
    except Exception as exc:
        write_error("inference_error", str(exc))
        return 1

    sys.stdout.write(json.dumps({"ok": True, "response": response_payload}, ensure_ascii=False))
    return 0


def write_error(error_type, error_message):
    sys.stdout.write(
        json.dumps(
            {
                "ok": False,
                "error_type": error_type,
                "error": error_message,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
