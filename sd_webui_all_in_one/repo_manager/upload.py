"""上传本地文件夹到仓库"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from sd_webui_all_in_one.file_manager import get_file_list
from sd_webui_all_in_one.config import RETRY_TIMES
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.repo_manager.types import (
    ApiType,
    RepoType,
)
from sd_webui_all_in_one.repo_manager.shared import logger
from sd_webui_all_in_one.repo_manager.utils import (
    _add_revision,
    _normalize_path_in_repo,
    _join_repo_path,
    _file_sha256,
)
from sd_webui_all_in_one.repo_manager.metadata import (
    _repo_file_metadata_by_path,
    _normalize_sha256,
)
from sd_webui_all_in_one.repo_manager.listing import RepoListingMixin
from sd_webui_all_in_one.repo_manager.repository import RepoCheckMixin


class RepoUploadMixin(RepoCheckMixin, RepoListingMixin):
    """上传本地文件夹到仓库的功能"""

    def upload_files_to_repo(
        self,
        api_type: ApiType,
        repo_id: str,
        upload_path: Path,
        repo_type: RepoType = "model",
        path_in_repo: str | None = None,
        visibility: bool = False,
        num_threads: int = 1,
        revision: str | None = None,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace / ModelScope 仓库中

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                仓库 ID
            upload_path (Path):
                要上传的文件夹
            repo_type (RepoType):
                仓库类型
            path_in_repo (str | None):
                仓库中的上传路径前缀, 为`None`时上传到仓库根目录
            visibility (bool):
                当仓库不存在时自动创建的仓库的可见性
            num_threads (int):
                上传线程数
            revision (str | None):
                指定上传目标分支或标签, 为`None`时使用第三方库默认值

        Raises:
            ValueError:
                API 类型未知时
        """
        if api_type not in ["huggingface", "modelscope"]:
            raise ValueError(f"未知的 API 类型: {api_type}")

        normalized_path_in_repo = _normalize_path_in_repo(path_in_repo)

        self.check_repo(
            api_type=api_type,
            repo_id=repo_id,
            repo_type=repo_type,
            visibility=visibility,
        )

        if api_type == "huggingface":
            self.upload_files_to_huggingface(
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "upload_path": upload_path,
                        "path_in_repo": normalized_path_in_repo,
                        "num_threads": num_threads,
                    },
                    revision,
                )
            )
        elif api_type == "modelscope":
            self.upload_files_to_modelscope(
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "upload_path": upload_path,
                        "path_in_repo": normalized_path_in_repo,
                        "num_threads": num_threads,
                    },
                    revision,
                )
            )

    def upload_files_to_huggingface(
        self,
        repo_id: str,
        upload_path: Path,
        repo_type: RepoType = "model",
        path_in_repo: str | None = None,
        num_threads: int = 1,
        revision: str | None = None,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace 仓库中

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            repo_type (RepoType):
                HuggingFace 仓库类型
            upload_path (Path):
                要上传到 HuggingFace 仓库的文件夹
            path_in_repo (str | None):
                仓库中的上传路径前缀, 为`None`时上传到仓库根目录
            num_threads (int):
                上传线程数
            revision (str | None):
                指定上传目标分支或标签, 为`None`时使用 HuggingFace 默认值

        Raises:
            AggregateError:
                上传任务出现错误时
        """
        normalized_path_in_repo = _normalize_path_in_repo(path_in_repo)
        upload_files = get_file_list(upload_path)
        repo_files = _repo_file_metadata_by_path(
            self.get_repo_files_metadata(
                api_type="huggingface",
                repo_id=repo_id,
                repo_type=repo_type,
                revision=revision,
            )
        )
        logger.info("上传到 HuggingFace 仓库: %s -> HuggingFace/%s", upload_path, repo_id)
        files_count = len(upload_files)
        err: list[Exception] = []
        upload_tasks: list[Path] = []

        for index, upload_file in enumerate(upload_files, start=1):
            upload_file_rel_path = _join_repo_path(normalized_path_in_repo, upload_file.relative_to(upload_path).as_posix())
            repo_file_metadata = repo_files.get(upload_file_rel_path)
            if repo_file_metadata is None:
                upload_tasks.append(upload_file)
                continue

            remote_sha256 = _normalize_sha256(repo_file_metadata.get("sha256"))
            local_sha256 = _file_sha256(upload_file)
            if remote_sha256 is None or local_sha256 != remote_sha256:
                upload_tasks.append(upload_file)
                logger.info(
                    "[%s/%s] %s 已存在于 HuggingFace 仓库中但 hash 缺失或不同, 将重新上传",
                    index,
                    files_count,
                    upload_file,
                )
                continue

            logger.info(
                "[%s/%s] %s 已存在于 HuggingFace 仓库中且 hash 相同, 跳过上传",
                index,
                files_count,
                upload_file,
            )

        @retryable(
            times=RETRY_TIMES,
            describe="上传文件到 HuggingFace",
            catch_exceptions=(Exception),
            raise_exception=(RuntimeError),
            retry_on_none=False,
        )
        def _upload_file(
            repo_id: str,
            repo_type: str,
            file_path_in_repo: str,
            path_or_fileobj: Path,
        ) -> None:
            upload_kwargs = _add_revision(
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "path_in_repo": file_path_in_repo,
                    "path_or_fileobj": path_or_fileobj,
                    "commit_message": f"Upload {path_or_fileobj.name}",
                },
                revision,
            )
            self.hf_api.upload_file(**upload_kwargs)

        if upload_tasks:
            logger.info("实际需要上传文件数量: %s", len(upload_tasks))
        upload_count = len(upload_tasks)

        err_lock = Lock()

        def _run_upload(
            task: tuple[int, Path],
        ) -> None:
            index, upload_file = task
            upload_file_rel_path = _join_repo_path(normalized_path_in_repo, upload_file.relative_to(upload_path).as_posix())
            logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中", index, upload_count, upload_file, repo_id, repo_type)
            try:
                _upload_file(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    file_path_in_repo=upload_file_rel_path,
                    path_or_fileobj=upload_file,
                )
            except RuntimeError as e:
                with err_lock:
                    err.append(e)
                logger.error("[%s/%s] 上传 %s 最终失败: %s", index, upload_count, upload_file.name, e)

        max_workers = max(1, num_threads)
        if max_workers == 1:
            for task in enumerate(upload_tasks, start=1):
                _run_upload(task)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(executor.map(_run_upload, enumerate(upload_tasks, start=1)))

        if err:
            raise AggregateError(f"上传 {repo_id} (类型: {repo_type}) 时发生了错误", err)

        logger.info("上传 %s 到 %s (类型: %s) 完成", upload_path, repo_id, repo_type)

    def upload_files_to_modelscope(
        self,
        repo_id: str,
        upload_path: Path,
        repo_type: RepoType = "model",
        path_in_repo: str | None = None,
        num_threads: int = 1,
        revision: str | None = None,
    ) -> None:
        """上传文件夹中的内容到 ModelScope 仓库中

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            repo_type (RepoType):
                ModelScope 仓库类型
            upload_path (Path):
                要上传到 ModelScope 仓库的文件夹
            path_in_repo (str | None):
                仓库中的上传路径前缀, 为`None`时上传到仓库根目录
            num_threads (int):
                上传线程数
            revision (str | None):
                指定上传目标分支或标签, 为`None`时使用 ModelScope 默认值

        Raises:
            AggregateError:
                上传任务出现错误时
        """
        normalized_path_in_repo = _normalize_path_in_repo(path_in_repo)
        upload_files = get_file_list(upload_path)
        repo_files = _repo_file_metadata_by_path(
            self.get_repo_files_metadata(
                api_type="modelscope",
                repo_id=repo_id,
                repo_type=repo_type,
                revision=revision,
            )
        )
        logger.info("上传到 ModelScope 仓库: %s -> ModelScope/%s", upload_path, repo_id)
        files_count = len(upload_files)
        err: list[Exception] = []
        upload_tasks: list[Path] = []

        for index, upload_file in enumerate(upload_files, start=1):
            upload_file_rel_path = _join_repo_path(normalized_path_in_repo, upload_file.relative_to(upload_path).as_posix())
            repo_file_metadata = repo_files.get(upload_file_rel_path)
            if repo_file_metadata is None:
                upload_tasks.append(upload_file)
                continue

            remote_sha256 = _normalize_sha256(repo_file_metadata.get("sha256"))
            local_sha256 = _file_sha256(upload_file)
            if remote_sha256 is None or local_sha256 != remote_sha256:
                upload_tasks.append(upload_file)
                logger.info(
                    "[%s/%s] %s 已存在于 ModelScope 仓库中但 hash 缺失或不同, 将重新上传",
                    index,
                    files_count,
                    upload_file,
                )
                continue

            logger.info(
                "[%s/%s] %s 已存在于 ModelScope 仓库中且 hash 相同, 跳过上传",
                index,
                files_count,
                upload_file,
            )

        @retryable(
            times=RETRY_TIMES,
            describe="上传文件到 ModelScope",
            catch_exceptions=(Exception),
            raise_exception=(RuntimeError),
            retry_on_none=False,
        )
        def _upload_file(
            repo_id: str,
            repo_type: str,
            file_path_in_repo: str,
            path_or_fileobj: Path,
        ) -> None:
            upload_kwargs = _add_revision(
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "path_in_repo": file_path_in_repo,
                    "path_or_fileobj": path_or_fileobj,
                    "commit_message": f"Upload {path_or_fileobj.name}",
                    "token": self.ms_token,
                },
                revision,
            )
            self.ms_api.upload_file(**upload_kwargs)

        if upload_tasks:
            logger.info("实际需要上传文件数量: %s", len(upload_tasks))
        upload_count = len(upload_tasks)

        err_lock = Lock()

        def _run_upload(
            task: tuple[int, Path],
        ) -> None:
            index, upload_file = task
            upload_file_rel_path = _join_repo_path(normalized_path_in_repo, upload_file.relative_to(upload_path).as_posix())
            logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中", index, upload_count, upload_file, repo_id, repo_type)
            try:
                _upload_file(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    file_path_in_repo=upload_file_rel_path,
                    path_or_fileobj=upload_file,
                )
            except RuntimeError as e:
                with err_lock:
                    err.append(e)
                logger.error("[%s/%s] 上传 %s 最终失败: %s", index, upload_count, upload_file.name, e)

        max_workers = max(1, num_threads)
        if max_workers == 1:
            for task in enumerate(upload_tasks, start=1):
                _run_upload(task)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(executor.map(_run_upload, enumerate(upload_tasks, start=1)))

        if err:
            raise AggregateError(f"上传 {repo_id} (类型: {repo_type}) 时发生了错误", err)

        logger.info("上传 %s 到 %s (类型: %s) 完成", upload_path, repo_id, repo_type)
