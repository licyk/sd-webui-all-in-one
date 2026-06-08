import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from huggingface_hub import HfApi
from modelscope.hub.api import HubApi


def get_package_folder() -> str:
    workspace = os.environ.get("WORKSPACE")
    if not workspace:
        raise RuntimeError("WORKSPACE environment variable is not set")

    folder_path = Path(workspace) / "sdnote"
    if not folder_path.is_dir():
        raise FileNotFoundError(f"Portable package folder does not exist: {folder_path}")

    return str(folder_path)


def upload_to_huggingface(folder_path: str) -> None:
    api = HfApi()
    api.upload_folder(
        repo_id="licyk/sdnote",
        repo_type="model",
        folder_path=folder_path,
    )


def upload_to_modelscope(folder_path: str) -> None:
    token = os.environ.get("MODELSCOPE_API_TOKEN")
    if not token:
        raise RuntimeError("MODELSCOPE_API_TOKEN environment variable is not set")

    api = HubApi()
    api.login(token)
    api.upload_folder(
        repo_id="licyks/sdnote",
        repo_type="model",
        folder_path=folder_path,
    )


def run_upload(name: str, upload_func, folder_path: str) -> None:
    print(f"Start uploading portable package to {name}", flush=True)
    upload_func(folder_path)
    print(f"Finished uploading portable package to {name}", flush=True)


def main() -> int:
    folder_path = get_package_folder()
    upload_tasks = {
        "HuggingFace": upload_to_huggingface,
        "ModelScope": upload_to_modelscope,
    }
    failed_targets = []

    with ThreadPoolExecutor(max_workers=len(upload_tasks)) as executor:
        future_to_name = {
            executor.submit(run_upload, name, upload_func, folder_path): name
            for name, upload_func in upload_tasks.items()
        }

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                future.result()
            except Exception as exc:
                failed_targets.append(name)
                print(f"{name} upload failed: {exc}", file=sys.stderr, flush=True)
                traceback.print_exception(type(exc), exc, exc.__traceback__)

    if failed_targets:
        print(f"Upload failed: {', '.join(failed_targets)}", file=sys.stderr, flush=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
