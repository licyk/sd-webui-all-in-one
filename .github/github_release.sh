#!/bin/bash

if [[ -z "${github_files}" ]]; then
    echo "github_files 环境变量未设置"
    exit 1
fi

if [[ -z "${github_release_tag}" ]]; then
    echo "github_release_tag 环境变量未设置"
    exit 1
fi

echo "${github_files}" | while IFS= read -r file_path; do
    [[ -z "${file_path}" ]] && continue
    echo "上传文件: ${file_path}"
    gh release delete-asset "${github_release_tag}" "$(basename "${file_path}")" -y || true
    gh release upload "${github_release_tag}" "${file_path}"
done
