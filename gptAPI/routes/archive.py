import mimetypes
import os
import urllib.parse
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(prefix="/archive")


def get_default_archive_source_path():
    container_archive_source_path = Path("/app/gpt_analysis/archive")

    if container_archive_source_path.exists():
        return container_archive_source_path

    project_archive_source_path = Path(__file__).resolve().parents[1] / "gpt_analysis" / "archive"

    if project_archive_source_path.exists():
        return project_archive_source_path

    return container_archive_source_path


def get_default_archive_readme_source_path():
    container_archive_readme_source_path = Path("/app/gpt_analysis/archive/README")

    if container_archive_readme_source_path.exists():
        return container_archive_readme_source_path

    project_archive_readme_source_path = Path(__file__).resolve().parents[1] / "gpt_analysis" / "archive" / "README"

    if project_archive_readme_source_path.exists():
        return project_archive_readme_source_path

    return container_archive_readme_source_path


ARCHIVE_TEXT_EXTENSIONS = {
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".ipynb",
    ".js",
    ".json",
    ".jsx",
    ".log",
    ".md",
    ".py",
    ".sh",
    ".sql",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
ARCHIVE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}
ARCHIVE_PREVIEW_MAX_BYTES = int(os.environ.get("ARCHIVE_PREVIEW_MAX_BYTES", "1048576"))
ARCHIVE_VISIBLE_ROOT_FOLDER_NAMES = ("논문", "증빙자료")
ARCHIVE_README_FOLDER_NAME = "README"
ARCHIVE_SOURCE_PATH = Path(
    os.environ.get("ARCHIVE_SOURCE_PATH", str(get_default_archive_source_path()))
).expanduser().resolve(strict=False)
ARCHIVE_README_SOURCE_PATH = Path(
    os.environ.get("ARCHIVE_README_SOURCE_PATH", str(get_default_archive_readme_source_path()))
).expanduser().resolve(strict=False)


@router.get("")
def read_archive_folder(path=""):
    try:
        if is_archive_root_path(path):
            return read_visible_archive_root()

        if is_archive_readme_path(path):
            return read_archive_readme_folder(path)

        ensure_visible_archive_path(path)
        current_folder = resolve_archive_folder(path)
        folders, files = list_archive_entries(current_folder)

        return {
            "success": True,
            "rootPath": str(ARCHIVE_SOURCE_PATH),
            "currentPath": get_archive_relative_path(current_folder),
            "parentPath": get_archive_parent_path(current_folder),
            "breadcrumbs": build_archive_breadcrumbs(current_folder),
            "folderCount": len(folders),
            "fileCount": len(files),
            "folders": folders,
            "files": files,
        }
    except ValueError as error:
        return make_archive_error_response(error)


@router.get("/preview")
def read_archive_file_preview(path=""):
    try:
        if is_archive_readme_path(path):
            return read_archive_readme_file_preview(path)

        ensure_visible_archive_path(path)
        archive_file_path = resolve_archive_file(path)

        if not is_archive_text_file(archive_file_path):
            raise ValueError("미리보기를 지원하지 않는 파일입니다.")

        if archive_file_path.stat().st_size > ARCHIVE_PREVIEW_MAX_BYTES:
            raise ValueError("미리보기 가능한 파일 크기를 초과했습니다.")

        file_content, encoding = read_archive_text_file(archive_file_path)

        return {
            "success": True,
            "path": get_archive_relative_path(archive_file_path),
            "name": archive_file_path.name,
            "encoding": encoding,
            "content": file_content,
        }
    except ValueError as error:
        return make_archive_error_response(error)


@router.get("/file")
def read_archive_file(path=""):
    try:
        if is_archive_readme_path(path):
            archive_file_path = resolve_archive_readme_file(path)
            media_type = mimetypes.guess_type(archive_file_path.name)[0] or "application/octet-stream"

            return FileResponse(
                archive_file_path,
                media_type=media_type,
                headers={
                    "Content-Disposition": make_archive_content_disposition("inline", archive_file_path.name),
                },
            )

        ensure_visible_archive_path(path)
        archive_file_path = resolve_archive_file(path)
        media_type = mimetypes.guess_type(archive_file_path.name)[0] or "application/octet-stream"

        return FileResponse(
            archive_file_path,
            media_type=media_type,
            headers={
                "Content-Disposition": make_archive_content_disposition("inline", archive_file_path.name),
            },
        )
    except ValueError as error:
        return make_archive_error_response(error)


@router.get("/download")
def download_archive_file(path=""):
    try:
        if is_archive_readme_path(path):
            archive_file_path = resolve_archive_readme_file(path)
            media_type = mimetypes.guess_type(archive_file_path.name)[0] or "application/octet-stream"

            return FileResponse(
                archive_file_path,
                media_type=media_type,
                filename=archive_file_path.name,
            )

        ensure_visible_archive_path(path)
        archive_file_path = resolve_archive_file(path)
        media_type = mimetypes.guess_type(archive_file_path.name)[0] or "application/octet-stream"

        return FileResponse(
            archive_file_path,
            media_type=media_type,
            filename=archive_file_path.name,
        )
    except ValueError as error:
        return make_archive_error_response(error)


def make_archive_error_response(error):
    return JSONResponse(
        content={
            "success": False,
            "error": str(error),
        },
        status_code=400,
    )


def get_archive_path_parts(relative_path):
    requested_relative_path = Path(str(relative_path or ""))

    if requested_relative_path.is_absolute() or ".." in requested_relative_path.parts:
        raise ValueError("허용되지 않은 archive 경로입니다.")

    return [path_part for path_part in requested_relative_path.parts if path_part not in ("", ".")]


def is_archive_root_path(relative_path):
    return len(get_archive_path_parts(relative_path)) == 0


def is_archive_readme_path(relative_path):
    path_parts = get_archive_path_parts(relative_path)
    return bool(path_parts) and path_parts[0] == ARCHIVE_README_FOLDER_NAME


def ensure_visible_archive_path(relative_path):
    path_parts = get_archive_path_parts(relative_path)

    if not path_parts or path_parts[0] not in ARCHIVE_VISIBLE_ROOT_FOLDER_NAMES:
        raise ValueError("허용되지 않은 archive 경로입니다.")


def read_visible_archive_root():
    visible_folders = []

    if ARCHIVE_SOURCE_PATH.exists() and ARCHIVE_SOURCE_PATH.is_dir():
        archive_folder_map = {
            child_path.name: child_path
            for child_path in ARCHIVE_SOURCE_PATH.iterdir()
            if child_path.is_dir()
        }

        for folder_name in ARCHIVE_VISIBLE_ROOT_FOLDER_NAMES:
            folder_path = archive_folder_map.get(folder_name)

            if folder_path is not None:
                visible_folders.append(build_archive_folder_entry(folder_path))

    if ARCHIVE_README_SOURCE_PATH.exists() and ARCHIVE_README_SOURCE_PATH.is_dir():
        visible_folders.append(build_archive_readme_folder_entry(ARCHIVE_README_SOURCE_PATH))

    return {
        "success": True,
        "rootPath": str(ARCHIVE_SOURCE_PATH),
        "currentPath": "",
        "parentPath": None,
        "breadcrumbs": build_archive_root_breadcrumbs(),
        "folderCount": len(visible_folders),
        "fileCount": 0,
        "folders": visible_folders,
        "files": [],
    }


def read_archive_readme_folder(path):
    current_folder = resolve_archive_readme_folder(path)
    folders, files = list_archive_readme_entries(current_folder)

    return {
        "success": True,
        "rootPath": str(ARCHIVE_README_SOURCE_PATH),
        "currentPath": get_archive_readme_relative_path(current_folder),
        "parentPath": get_archive_readme_parent_path(current_folder),
        "breadcrumbs": build_archive_readme_breadcrumbs(current_folder),
        "folderCount": len(folders),
        "fileCount": len(files),
        "folders": folders,
        "files": files,
    }


def read_archive_readme_file_preview(path):
    archive_file_path = resolve_archive_readme_file(path)

    if not is_archive_text_file(archive_file_path):
        raise ValueError("미리보기를 지원하지 않는 파일입니다.")

    if archive_file_path.stat().st_size > ARCHIVE_PREVIEW_MAX_BYTES:
        raise ValueError("미리보기 가능한 파일 크기를 초과했습니다.")

    file_content, encoding = read_archive_text_file(archive_file_path)

    return {
        "success": True,
        "path": get_archive_readme_relative_path(archive_file_path),
        "name": archive_file_path.name,
        "encoding": encoding,
        "content": file_content,
    }


def resolve_archive_folder(relative_path):
    archive_path = resolve_archive_path(relative_path)

    if not archive_path.exists() or not archive_path.is_dir():
        raise ValueError("archive 폴더를 찾을 수 없습니다.")

    return archive_path


def resolve_archive_file(relative_path):
    archive_path = resolve_archive_path(relative_path)

    if not archive_path.exists() or not archive_path.is_file():
        raise ValueError("archive 파일을 찾을 수 없습니다.")

    return archive_path


def resolve_archive_readme_folder(relative_path):
    archive_path = resolve_archive_readme_path(relative_path)

    if not archive_path.exists() or not archive_path.is_dir():
        raise ValueError("README 폴더를 찾을 수 없습니다.")

    return archive_path


def resolve_archive_readme_file(relative_path):
    archive_path = resolve_archive_readme_path(relative_path)

    if not archive_path.exists() or not archive_path.is_file():
        raise ValueError("README 파일을 찾을 수 없습니다.")

    return archive_path


def resolve_archive_path(relative_path):
    requested_relative_path = Path(str(relative_path or ""))

    if requested_relative_path.is_absolute() or ".." in requested_relative_path.parts:
        raise ValueError("허용되지 않은 archive 경로입니다.")

    archive_path = (ARCHIVE_SOURCE_PATH / requested_relative_path).resolve(strict=False)
    ensure_archive_path_is_allowed(archive_path)

    return archive_path


def resolve_archive_readme_path(relative_path):
    path_parts = get_archive_path_parts(relative_path)

    if not path_parts or path_parts[0] != ARCHIVE_README_FOLDER_NAME:
        raise ValueError("허용되지 않은 archive 경로입니다.")

    readme_relative_path = Path(*path_parts[1:]) if len(path_parts) > 1 else Path("")
    archive_path = (ARCHIVE_README_SOURCE_PATH / readme_relative_path).resolve(strict=False)
    ensure_archive_readme_path_is_allowed(archive_path)

    return archive_path


def ensure_archive_path_is_allowed(archive_path):
    try:
        archive_path.relative_to(ARCHIVE_SOURCE_PATH)
    except ValueError:
        raise ValueError("허용되지 않은 archive 경로입니다.")


def ensure_archive_readme_path_is_allowed(archive_path):
    try:
        archive_path.relative_to(ARCHIVE_README_SOURCE_PATH)
    except ValueError:
        raise ValueError("허용되지 않은 archive 경로입니다.")


def list_archive_entries(current_folder):
    folders = []
    files = []

    for child_path in sorted(current_folder.iterdir(), key=get_archive_sort_key):
        try:
            ensure_archive_path_is_allowed(child_path.resolve(strict=False))
        except ValueError:
            continue

        if child_path.is_dir():
            folders.append(build_archive_folder_entry(child_path))
        elif child_path.is_file():
            files.append(build_archive_file_entry(child_path))

    return folders, files


def list_archive_readme_entries(current_folder):
    folders = []
    files = []

    for child_path in sorted(current_folder.iterdir(), key=get_archive_sort_key):
        try:
            ensure_archive_readme_path_is_allowed(child_path.resolve(strict=False))
        except ValueError:
            continue

        if child_path.is_dir():
            folders.append(build_archive_readme_folder_entry(child_path))
        elif child_path.is_file():
            files.append(build_archive_readme_file_entry(child_path))

    return folders, files


def get_archive_sort_key(archive_path):
    return (not archive_path.is_dir(), archive_path.name.lower())


def build_archive_folder_entry(folder_path):
    return {
        "name": folder_path.name,
        "path": get_archive_relative_path(folder_path),
        "modifiedAt": folder_path.stat().st_mtime,
    }


def build_archive_file_entry(file_path):
    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    return {
        "name": file_path.name,
        "path": get_archive_relative_path(file_path),
        "extension": file_path.suffix.lower(),
        "size": file_path.stat().st_size,
        "modifiedAt": file_path.stat().st_mtime,
        "mediaType": media_type,
        "previewType": get_archive_preview_type(file_path, media_type),
    }


def build_archive_readme_folder_entry(folder_path):
    return {
        "name": folder_path.name if folder_path != ARCHIVE_README_SOURCE_PATH else ARCHIVE_README_FOLDER_NAME,
        "path": get_archive_readme_relative_path(folder_path),
        "modifiedAt": folder_path.stat().st_mtime,
    }


def build_archive_readme_file_entry(file_path):
    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    return {
        "name": file_path.name,
        "path": get_archive_readme_relative_path(file_path),
        "extension": file_path.suffix.lower(),
        "size": file_path.stat().st_size,
        "modifiedAt": file_path.stat().st_mtime,
        "mediaType": media_type,
        "previewType": get_archive_preview_type(file_path, media_type),
    }


def get_archive_relative_path(archive_path):
    relative_path = archive_path.relative_to(ARCHIVE_SOURCE_PATH)

    if str(relative_path) == ".":
        return ""

    return str(relative_path).replace(os.sep, "/")


def get_archive_readme_relative_path(archive_path):
    relative_path = archive_path.relative_to(ARCHIVE_README_SOURCE_PATH)

    if str(relative_path) == ".":
        return ARCHIVE_README_FOLDER_NAME

    return f"{ARCHIVE_README_FOLDER_NAME}/{str(relative_path).replace(os.sep, '/')}"


def get_archive_parent_path(current_folder):
    if current_folder == ARCHIVE_SOURCE_PATH:
        return None

    return get_archive_relative_path(current_folder.parent)


def get_archive_readme_parent_path(current_folder):
    if current_folder == ARCHIVE_README_SOURCE_PATH:
        return ""

    return get_archive_readme_relative_path(current_folder.parent)


def build_archive_root_breadcrumbs():
    return [
        {
            "label": "Archive",
            "path": "",
        }
    ]


def build_archive_breadcrumbs(current_folder):
    breadcrumbs = build_archive_root_breadcrumbs()

    current_relative_path = get_archive_relative_path(current_folder)

    if not current_relative_path:
        return breadcrumbs

    path_parts = current_relative_path.split("/")
    current_path_parts = []

    for path_part in path_parts:
        current_path_parts.append(path_part)
        breadcrumbs.append(
            {
                "label": path_part,
                "path": "/".join(current_path_parts),
            }
        )

    return breadcrumbs


def build_archive_readme_breadcrumbs(current_folder):
    breadcrumbs = build_archive_root_breadcrumbs()
    current_relative_path = get_archive_readme_relative_path(current_folder)
    path_parts = current_relative_path.split("/")
    current_path_parts = []

    for path_part in path_parts:
        current_path_parts.append(path_part)
        breadcrumbs.append(
            {
                "label": path_part,
                "path": "/".join(current_path_parts),
            }
        )

    return breadcrumbs


def get_archive_preview_type(file_path, media_type):
    if is_archive_text_file(file_path):
        return "text"

    if file_path.suffix.lower() in ARCHIVE_IMAGE_EXTENSIONS:
        return "image"

    if media_type == "application/pdf":
        return "pdf"

    return "download"


def is_archive_text_file(file_path):
    media_type = mimetypes.guess_type(file_path.name)[0] or ""

    return file_path.suffix.lower() in ARCHIVE_TEXT_EXTENSIONS or media_type.startswith("text/")


def read_archive_text_file(file_path):
    file_bytes = file_path.read_bytes()

    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return file_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    raise ValueError("텍스트 파일 인코딩을 읽을 수 없습니다.")


def make_archive_content_disposition(disposition, file_name):
    encoded_file_name = urllib.parse.quote(file_name)
    return f"{disposition}; filename*=UTF-8''{encoded_file_name}"
