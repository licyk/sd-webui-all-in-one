"""HuggingFace / ModelScope 仓库文件镜像"""

import os
import shutil
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from sd_webui_all_in_one.config import RETRY_TIMES
from sd_webui_all_in_one.downloader import (
    DownloadToolType,
    download_file,
)
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.repo_manager.types import (
    ApiType,
    RepoType,
    MirrorGroupTask,
)
from sd_webui_all_in_one.repo_manager.shared import logger
from sd_webui_all_in_one.repo_manager.utils import _add_revision
from sd_webui_all_in_one.repo_manager.metadata import (
    _repo_file_metadata_by_path,
    _repo_file_hash_matches,
    _normalize_file_size,
)
from sd_webui_all_in_one.repo_manager.dependencies import _ensure_modelscope
from sd_webui_all_in_one.repo_manager.grouping import (
    _format_size,
    _get_free_disk_space,
    _plan_mirror_group,
)
from sd_webui_all_in_one.repo_manager.listing import RepoListingMixin
from sd_webui_all_in_one.repo_manager.urls import RepoDownloadUrlMixin
from sd_webui_all_in_one.repo_manager.repository import RepoCheckMixin


class RepoMirrorMixin(RepoCheckMixin, RepoListingMixin, RepoDownloadUrlMixin):
    """仓库文件镜像功能"""

    def mirror_repo_files(
        self,
        src_api_type: ApiType,
        dst_api_type: ApiType,
        src_repo_id: str,
        dst_repo_id: str,
        src_repo_type: RepoType = "model",
        dst_repo_type: RepoType = "model",
        visibility: bool = False,
        revision: str | None = None,
        num_threads: int = 1,
        retry_times: int = RETRY_TIMES,
        use_fast_download: bool = False,
        download_tool: DownloadToolType | None = "requests",
        download_split: int = 5,
        download_progress: bool = True,
        use_group_mirror: bool = False,
        group_size: int = 10,
        reserved_disk_space_gb: float = 5.0,
        work_dir: Path | None = None,
    ) -> None:
        """镜像 HuggingFace / ModelScope 仓库文件

        默认模式下每个文件单独下载并单独提交。启用`use_group_mirror`后进入分组镜像模式:
        每组根据当前剩余磁盘空间 (扣除`reserved_disk_space_gb`) 和`group_size`动态规划,
        组内文件全部下载结束后作为一次提交上传到目标仓库, 清理本地文件后再规划下一组。
        组内下载失败的文件不会阻止其余文件提交, 所有失败会在最后统一抛出。

        Args:
            src_api_type (ApiType):
                源仓库 API 类型
            dst_api_type (ApiType):
                目标仓库 API 类型
            src_repo_id (str):
                源仓库 ID
            dst_repo_id (str):
                目标仓库 ID
            src_repo_type (RepoType):
                源仓库类型
            dst_repo_type (RepoType):
                目标仓库类型
            visibility (bool):
                当目标仓库不存在时自动创建的仓库的可见性
            revision (str | None):
                指定源仓库读取和目标仓库上传的分支、标签或提交哈希, 为`None`时使用第三方库默认值
            num_threads (int):
                镜像线程数
            retry_times (int):
                单个文件镜像失败后的重试次数
            use_fast_download (bool):
                是否使用项目内`download_file()`下载器进行下载
            download_tool (DownloadToolType | None):
                `use_fast_download`启用时使用的下载器
            download_split (int):
                `use_fast_download`启用时传给`download_file()`的下载 split
            download_progress (bool):
                `use_fast_download`启用时是否显示下载进度
            use_group_mirror (bool):
                是否启用分组镜像模式, 每组文件下载完成后作为一次提交上传
            group_size (int):
                分组镜像模式下每组的最大文件数量
            reserved_disk_space_gb (float):
                分组镜像模式下保留不使用的磁盘空间 (GB)
            work_dir (Path | None):
                分组镜像模式下的临时下载目录, 同时用于计算剩余磁盘空间, 为`None`时使用系统临时目录

        Raises:
            AggregateError:
                镜像任务出现错误时
            ValueError:
                API 类型未知或分组镜像参数无效时
        """
        if src_api_type not in ["huggingface", "modelscope"]:
            raise ValueError(f"未知的源 API 类型: {src_api_type}")
        if dst_api_type not in ["huggingface", "modelscope"]:
            raise ValueError(f"未知的目标 API 类型: {dst_api_type}")
        if use_group_mirror:
            if group_size < 1:
                raise ValueError(f"分组镜像的每组文件数量必须大于 0: {group_size}")
            if reserved_disk_space_gb < 0:
                raise ValueError(f"分组镜像的保留磁盘空间不能为负数: {reserved_disk_space_gb}")

        logger.info(
            "镜像仓库文件: %s/%s (类型: %s) -> %s/%s (类型: %s)",
            src_api_type,
            src_repo_id,
            src_repo_type,
            dst_api_type,
            dst_repo_id,
            dst_repo_type,
        )

        self.check_repo(
            api_type=dst_api_type,
            repo_id=dst_repo_id,
            repo_type=dst_repo_type,
            visibility=visibility,
        )

        src_files = _repo_file_metadata_by_path(
            self.get_repo_files_metadata(
                api_type=src_api_type,
                repo_id=src_repo_id,
                repo_type=src_repo_type,
                revision=revision,
            )
        )
        dst_files = _repo_file_metadata_by_path(
            self.get_repo_files_metadata(
                api_type=dst_api_type,
                repo_id=dst_repo_id,
                repo_type=dst_repo_type,
                revision=revision,
            )
        )

        mirror_tasks: list[str] = []
        files_count = len(src_files)
        for index, (repo_file, src_metadata) in enumerate(src_files.items(), start=1):
            dst_metadata = dst_files.get(repo_file)
            if dst_metadata is None:
                mirror_tasks.append(repo_file)
                continue

            if not _repo_file_hash_matches(src_metadata, dst_metadata):
                mirror_tasks.append(repo_file)
                logger.info(
                    "[%s/%s] %s 已存在于目标仓库中但 hash 缺失或不同, 将重新镜像",
                    index,
                    files_count,
                    repo_file,
                )
                continue

            logger.info(
                "[%s/%s] %s 已存在于目标仓库中且 hash 相同, 跳过镜像",
                index,
                files_count,
                repo_file,
            )

        logger.info("需要镜像的文件数量: %s", len(mirror_tasks))
        if not mirror_tasks:
            logger.info("镜像仓库文件完成")
            return
        mirror_count = len(mirror_tasks)

        actual_retry_times = max(1, retry_times)

        def _download_source_file(repo_file: str, tmp_dir: Path) -> Path:
            file_path = tmp_dir / repo_file
            if use_fast_download:
                download_url = self.get_repo_file_download_url(
                    api_type=src_api_type,
                    repo_id=src_repo_id,
                    file_path=repo_file,
                    repo_type=src_repo_type,
                    revision=revision,
                )
                download_file(
                    url=download_url,
                    path=file_path.parent,
                    save_name=file_path.name,
                    tool=download_tool,
                    progress=download_progress,
                    split=download_split,
                )
            elif src_api_type == "huggingface":
                self.hf_api.hf_hub_download(
                    **_add_revision(
                        {
                            "repo_id": src_repo_id,
                            "repo_type": src_repo_type,
                            "filename": repo_file,
                            "local_dir": tmp_dir,
                        },
                        revision,
                    )
                )
            else:
                _ensure_modelscope()
                from modelscope import snapshot_download

                snapshot_download(
                    **_add_revision(
                        {
                            "repo_id": src_repo_id,
                            "repo_type": src_repo_type,
                            "allow_patterns": repo_file,
                            "local_dir": tmp_dir,
                        },
                        revision,
                    )
                )

            if not file_path.exists():
                raise FileNotFoundError(f"镜像下载后的文件不存在: {file_path}")
            return file_path

        if use_group_mirror:
            self._mirror_repo_files_grouped(
                mirror_tasks=[(repo_file, _normalize_file_size(src_files[repo_file].get("size"))) for repo_file in mirror_tasks],
                download_source_file=_download_source_file,
                src_repo_id=src_repo_id,
                dst_api_type=dst_api_type,
                dst_repo_id=dst_repo_id,
                dst_repo_type=dst_repo_type,
                revision=revision,
                num_threads=num_threads,
                retry_times=actual_retry_times,
                group_size=group_size,
                reserved_disk_space_gb=reserved_disk_space_gb,
                work_dir=work_dir,
            )
            return

        @retryable(
            times=actual_retry_times,
            describe="镜像仓库文件",
            catch_exceptions=(Exception),
            raise_exception=(RuntimeError),
            retry_on_none=False,
        )
        def _mirror_file(repo_file: str, index: int) -> None:
            with tempfile.TemporaryDirectory(prefix="repo-mirror-") as tmp_dir_str:
                logger.info("[%s/%s] 镜像 %s", index, mirror_count, repo_file)
                file_path = _download_source_file(repo_file, Path(tmp_dir_str))

                upload_kwargs = _add_revision(
                    {
                        "repo_id": dst_repo_id,
                        "repo_type": dst_repo_type,
                        "path_in_repo": repo_file,
                        "path_or_fileobj": file_path,
                        "commit_message": f"Mirror {repo_file}",
                    },
                    revision,
                )
                if dst_api_type == "huggingface":
                    self.hf_api.upload_file(**upload_kwargs)
                else:
                    upload_kwargs["token"] = self.ms_token
                    self.ms_api.upload_file(**upload_kwargs)

        err: list[Exception] = []
        err_lock = Lock()

        def _run_mirror(task: tuple[int, str]) -> None:
            index, repo_file = task
            try:
                _mirror_file(repo_file=repo_file, index=index)
            except RuntimeError as e:
                with err_lock:
                    err.append(e)
                logger.error("[%s/%s] 镜像 %s 最终失败: %s", index, mirror_count, repo_file, e)

        max_workers = max(1, num_threads)
        if max_workers == 1:
            for task in enumerate(mirror_tasks, start=1):
                _run_mirror(task)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(executor.map(_run_mirror, enumerate(mirror_tasks, start=1)))

        if err:
            raise AggregateError(f"镜像 {src_repo_id} -> {dst_repo_id} 时发生了错误", err)

        logger.info("镜像仓库文件完成")

    def _mirror_repo_files_grouped(
        self,
        mirror_tasks: list[MirrorGroupTask],
        download_source_file: Callable[[str, Path], Path],
        src_repo_id: str,
        dst_api_type: ApiType,
        dst_repo_id: str,
        dst_repo_type: RepoType,
        revision: str | None,
        num_threads: int,
        retry_times: int,
        group_size: int,
        reserved_disk_space_gb: float,
        work_dir: Path | None,
    ) -> None:
        """以分组模式镜像仓库文件

        每轮根据剩余磁盘空间规划一组文件, 下载完成后作为一次提交上传到目标仓库,
        并在清理本地文件后再规划下一组, 保证同一时间只有一组文件占用磁盘。

        Args:
            mirror_tasks (list[MirrorGroupTask]):
                需要镜像的文件及其大小
            download_source_file (Callable[[str, Path], Path]):
                将源仓库文件下载到指定目录并返回文件路径的函数
            src_repo_id (str):
                源仓库 ID
            dst_api_type (ApiType):
                目标仓库 API 类型
            dst_repo_id (str):
                目标仓库 ID
            dst_repo_type (RepoType):
                目标仓库类型
            revision (str | None):
                目标仓库上传的分支或标签
            num_threads (int):
                组内下载线程数
            retry_times (int):
                单个文件下载和单组提交的重试次数
            group_size (int):
                每组最大文件数量
            reserved_disk_space_gb (float):
                保留不使用的磁盘空间 (GB)
            work_dir (Path | None):
                临时下载目录, 为`None`时使用系统临时目录

        Raises:
            AggregateError:
                镜像任务出现错误时
        """
        actual_work_dir = Path(work_dir) if work_dir is not None else Path(tempfile.gettempdir())
        actual_work_dir.mkdir(parents=True, exist_ok=True)
        reserved_bytes = int(reserved_disk_space_gb * 1024**3)
        mirror_count = len(mirror_tasks)
        task_indexes = {repo_file: index for index, (repo_file, _) in enumerate(mirror_tasks, start=1)}
        pending = list(mirror_tasks)
        err: list[Exception] = []
        err_lock = Lock()
        group_index = 0
        committed_count = 0
        logger.info(
            "启用分组镜像, 每组最多 %s 个文件, 保留磁盘空间 %s, 工作目录: %s",
            group_size,
            _format_size(reserved_bytes),
            actual_work_dir,
        )

        @retryable(
            times=retry_times,
            describe="下载分组镜像文件",
            catch_exceptions=(Exception),
            raise_exception=(RuntimeError),
            retry_on_none=False,
        )
        def _download_group_file(repo_file: str, download_dir: Path, stage_dir: Path) -> None:
            # 每次尝试使用干净的目录, 避免失败残留的文件占用磁盘空间
            if download_dir.exists():
                shutil.rmtree(download_dir)
            download_dir.mkdir(parents=True)
            file_path = download_source_file(repo_file, download_dir)
            target_path = stage_dir / repo_file
            target_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(file_path, target_path)
            shutil.rmtree(download_dir, ignore_errors=True)

        @retryable(
            times=retry_times,
            describe="提交分组镜像文件",
            catch_exceptions=(Exception),
            raise_exception=(RuntimeError),
            retry_on_none=False,
        )
        def _commit_group(stage_dir: Path, commit_message: str) -> None:
            upload_kwargs = _add_revision(
                {
                    "repo_id": dst_repo_id,
                    "repo_type": dst_repo_type,
                    "folder_path": stage_dir,
                    "commit_message": commit_message,
                },
                revision,
            )
            if dst_api_type == "huggingface":
                self.hf_api.upload_folder(**upload_kwargs)
            else:
                upload_kwargs["token"] = self.ms_token
                self.ms_api.upload_folder(**upload_kwargs)

        def _download_group(group: list[MirrorGroupTask], group_dir: Path, stage_dir: Path) -> list[str]:
            downloaded: list[str] = []

            def _run_download(task: tuple[int, MirrorGroupTask]) -> None:
                slot, (repo_file, _) = task
                index = task_indexes[repo_file]
                logger.info("[%s/%s] 下载 %s", index, mirror_count, repo_file)
                try:
                    _download_group_file(
                        repo_file=repo_file,
                        download_dir=group_dir / "download" / str(slot),
                        stage_dir=stage_dir,
                    )
                except RuntimeError as e:
                    with err_lock:
                        err.append(e)
                    logger.error("[%s/%s] 下载 %s 最终失败: %s", index, mirror_count, repo_file, e)
                    return
                with err_lock:
                    downloaded.append(repo_file)

            max_workers = max(1, num_threads)
            if max_workers == 1:
                for task in enumerate(group):
                    _run_download(task)
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    list(executor.map(_run_download, enumerate(group)))
            return sorted(downloaded, key=lambda repo_file: task_indexes[repo_file])

        while pending:
            free_space = _get_free_disk_space(actual_work_dir)
            budget = free_space - reserved_bytes
            if budget <= 0:
                logger.error(
                    "剩余磁盘空间 %s 不足以满足保留空间 %s, 停止镜像剩余的 %s 个文件",
                    _format_size(free_space),
                    _format_size(reserved_bytes),
                    len(pending),
                )
                err.extend(RuntimeError(f"磁盘空间不足, 未镜像 {repo_file}") for repo_file, _ in pending)
                break

            group, too_large = _plan_mirror_group(pending, group_size, budget)
            for repo_file, size in too_large:
                logger.error(
                    "[%s/%s] %s 大小为 %s, 超过可用磁盘空间 %s (剩余 %s, 保留 %s), 跳过镜像",
                    task_indexes[repo_file],
                    mirror_count,
                    repo_file,
                    _format_size(size),
                    _format_size(budget),
                    _format_size(free_space),
                    _format_size(reserved_bytes),
                )
                err.append(RuntimeError(f"磁盘空间不足, 无法镜像 {repo_file} (大小: {_format_size(size)}, 可用空间: {_format_size(budget)})"))
            scheduled = {repo_file for repo_file, _ in group + too_large}
            pending = [task for task in pending if task[0] not in scheduled]
            if not group:
                continue

            group_index += 1
            planned_size = None if any(size is None for _, size in group) else sum(size or 0 for _, size in group)
            logger.info(
                "[分组 %s] 镜像 %s 个文件 (预计占用 %s), 剩余磁盘空间 %s, 保留空间 %s, 待规划文件 %s 个",
                group_index,
                len(group),
                _format_size(planned_size),
                _format_size(free_space),
                _format_size(reserved_bytes),
                len(pending),
            )

            with tempfile.TemporaryDirectory(prefix="repo-mirror-group-", dir=actual_work_dir) as group_dir_str:
                group_dir = Path(group_dir_str)
                stage_dir = group_dir / "stage"
                stage_dir.mkdir()
                downloaded = _download_group(group, group_dir, stage_dir)

                free_space_after = _get_free_disk_space(actual_work_dir)
                if free_space_after < reserved_bytes:
                    logger.warning(
                        "[分组 %s] 下载后剩余磁盘空间 %s 低于保留空间 %s, 源仓库的文件大小信息可能不准确",
                        group_index,
                        _format_size(free_space_after),
                        _format_size(reserved_bytes),
                    )

                if not downloaded:
                    logger.error("[分组 %s] 没有下载成功的文件, 跳过提交", group_index)
                    continue

                logger.info("[分组 %s] 提交 %s 个文件到 %s (类型: %s)", group_index, len(downloaded), dst_repo_id, dst_repo_type)
                try:
                    _commit_group(
                        stage_dir=stage_dir,
                        commit_message=f"Mirror {len(downloaded)} files (group {group_index})",
                    )
                except RuntimeError as e:
                    group_error = RuntimeError(f"提交分组 {group_index} 失败, 未镜像的文件: {', '.join(downloaded)}")
                    group_error.__cause__ = e
                    err.append(group_error)
                    logger.error("[分组 %s] 提交最终失败: %s", group_index, e)
                else:
                    committed_count += len(downloaded)
                    logger.info("[分组 %s] 提交完成, 已镜像 %s/%s 个文件", group_index, committed_count, mirror_count)

        if err:
            raise AggregateError(f"镜像 {src_repo_id} -> {dst_repo_id} 时发生了错误", err)

        logger.info("镜像仓库文件完成, 共提交 %s 个分组", group_index)
