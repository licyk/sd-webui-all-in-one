#!/bin/bash
set -e

if [[ -z "${github_files}" ]]; then
    echo "github_files 环境变量未设置"
    exit 1
fi

if [[ -z "${github_release_tag}" ]]; then
    echo "github_release_tag 环境变量未设置"
    exit 1
fi

# 使用 for 循环配合路径展开处理通配符
# 将环境变量按行读取, 并对每一行进行通配符展开
for pattern in ${github_files}; do
    # 使用 ls 找到所有匹配的文件 (处理 config/** 等情况)
    for file_path in $(ls -d $pattern 2>/dev/null); do
        # 排除目录, 只上传文件
        if [[ -f "$file_path" ]]; then
            filename=$(basename "${file_path}")
            echo "准备处理文件: ${file_path}"

            # 删除已存在的同名 Asset (防止重复上传报错)
            gh release delete-asset "${github_release_tag}" "$filename" -y || true

            echo "正在上传: ${file_path}"
            gh release upload "${github_release_tag}" "${file_path}" --clobber
        fi
    done
done