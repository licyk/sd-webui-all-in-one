"""Python Standalone 测试辅助工具"""

from sd_webui_all_in_one.python_standalone import release, resources
from sd_webui_all_in_one.python_standalone.types import RepoTarget

LINUX_312 = "cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.tar.gz"


WINDOWS_312 = "cpython-3.12.14+20260924-x86_64-pc-windows-msvc-install_only.tar.gz"


REPO_PATH_LINUX_312 = "python/linux/amd64/cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.zip"


HF = RepoTarget("huggingface", "user/hf-repo")


MS = RepoTarget("modelscope", "user/ms-repo")


def make_asset(name, sha256=None):
    asset = release.parse_asset_name(name, f"https://example.com/{name}", sha256=sha256)
    assert asset is not None
    return asset


def make_resource(version, build_date, platform="linux/amd64", variant="install_only"):
    system, arch = platform.split("/")
    triple = {"linux/amd64": "x86_64-unknown-linux-gnu", "windows/amd64": "x86_64-pc-windows-msvc"}[platform]
    path = f"python/{platform}/cpython-{version}+{build_date}-{triple}-{variant}.zip"
    resource = resources.parse_resource_path(path)
    assert resource is not None
    return resource


class FakeRepoManager:
    def __init__(self, files=None):
        self.files = files or {}
        self.uploads = []

    def get_repo_files_metadata(self, api_type, repo_id, repo_type="model", revision=None):
        return self.files.get(api_type, [])

    def upload_files_to_repo(self, api_type, repo_id, upload_path, repo_type, path_in_repo, visibility, num_threads, revision):
        files = sorted(p.relative_to(upload_path).as_posix() for p in upload_path.rglob("*") if p.is_file())
        self.uploads.append({"api_type": api_type, "repo_id": repo_id, "path_in_repo": path_in_repo, "files": files, "visibility": visibility, "num_threads": num_threads})
