#!/usr/bin/env python
# coding:utf-8
# tools: https://github.com/nICEnnnnnnnLee/action-gitee-release
# fork: https://github.com/licyk/action-gitee-release
# Gitee release id: https://gitee.com/api/v5/swagger#/getV5ReposOwnerRepoReleases
import os, glob
import requests,json,time
from requests_toolbelt import MultipartEncoder
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

retry_times = os.environ.get("gitee_upload_retry_times", "0")
try:
    retry_times = int(retry_times)
except:
    retry_times = 0
    
def Retry(retry, include_exceptions = [Exception], exclude_exceptions = [ValueError], sleep = 1):
    def decoratedRetry(func):
        def checkRun(retry, *args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if no_catch(e, exclude_exceptions) or not need_catch(e, include_exceptions):
                    raise e
                if(retry == 0):
                    raise e
                else:
                    print('error catched:', e)
                    if sleep > 0:
                        time.sleep(sleep)
                    return checkRun(retry-1, *args, **kwargs)
                    
        @wraps(func)      
        def run(*args, **kwargs):
            return checkRun(retry, *args, **kwargs)
        return run
    return decoratedRetry

def need_catch(exception, include_exceptions):
    for ex in include_exceptions:
        if isinstance(exception, ex):
            return True
    return False
    
def no_catch(exception, exclude_exceptions):
    for ex in exclude_exceptions:
        if isinstance(exception, ex):
            return True
    return False
    
class Gitee:
    def __init__(self, owner, token):
        self.owner = owner
        self.token = token

    def create_release(self, repo, tag_name, name, body = '-', target_commitish = 'master'):
        url = f'https://gitee.com/api/v5/repos/{self.owner}/{repo}/releases'
        data = {
            'access_token': self.token,
            'tag_name': tag_name,
            'name': name,
            'body': body,
            'target_commitish': target_commitish,
        }
        response = requests.post(url, data=data)
        res = response.json() 
        if response.status_code < 200 or response.status_code > 300:
            return False, res["message"] if "message" in res else f"Response status_code is {response.status_code}"
        
        if "id" in res:
            return True, res["id"]
        else:
            return False, "No 'id' in response"

    def get_release(self, repo, release_id):
        url = f'https://gitee.com/api/v5/repos/{self.owner}/{repo}/releases/{release_id}'
        data = {
            'access_token': self.token,
        }
        response = requests.get(url, data=data)
        res = response.json()
        if response.status_code < 200 or response.status_code > 300:
            return False, res["message"] if "message" in res else f"Response status_code is {response.status_code}"
        return True, res

    def update_release(self, repo, release_id, body, name=None, tag_name=None):
        if name is None or tag_name is None:
            success, release_info = self.get_release(repo, release_id)
            if not success:
                return False, release_info
            if name is None:
                name = release_info.get('name')
            if tag_name is None:
                tag_name = release_info.get('tag_name')

        url = f'https://gitee.com/api/v5/repos/{self.owner}/{repo}/releases/{release_id}'
        data = {
            'access_token': self.token,
            'body': body,
            'name': name,
            'tag_name': tag_name,
        }
        response = requests.patch(url, data=data)
        res = response.json()
        if response.status_code < 200 or response.status_code > 300:
            return False, res["message"] if "message" in res else f"Response status_code is {response.status_code}"
        
        if "id" in res:
            return True, res["id"]
        else:
            return False, "No 'id' in response"

    def get_release_id_by_tag(self, repo, tag_name):
        """Get release id by tag_name or name"""
        url = f'https://gitee.com/api/v5/repos/{self.owner}/{repo}/releases'
        data = {
            'access_token': self.token,
        }
        response = requests.get(url, data=data)
        res = response.json()
        if response.status_code < 200 or response.status_code > 300:
            return False, res["message"] if "message" in res else f"Response status_code is {response.status_code}"
        
        for release in res:
            if release.get("tag_name") == tag_name or release.get("name") == tag_name:
                return True, release.get("id")

        return False, f"Release with tag_name or name '{tag_name}' not found"

    def get_exist_file_id(self, repo, release_id, file_name):
        url = f'https://gitee.com/api/v5/repos/{self.owner}/{repo}/releases/{release_id}/attach_files'
        file_id_list = []
        data = {
            'access_token': self.token,
        }
        response = requests.get(url, data=data)
        res = response.json()
        if response.status_code < 200 or response.status_code > 300:
            return file_id_list

        for key in res:
            if key.get("name") == file_name:
                file_id_list.append(key.get("id"))

        return file_id_list

    def delete_exist_file(self, repo, release_id, file_name):
        data = {
            'access_token': self.token,
        }
        file_id_list = self.get_exist_file_id(repo, release_id, file_name)
        for attach_file_id in file_id_list:
            print(f"delete exists file: {file_name}, id: {attach_file_id}")
            url = f'https://gitee.com/api/v5/repos/{self.owner}/{repo}/releases/{release_id}/attach_files/{attach_file_id}'
            response = requests.delete(url, data=data)
            if response.status_code < 200 or response.status_code > 300:
                print("delete release exists file failed: {}".format(f"Response status_code is {response.status_code}"))

    @Retry(retry_times)
    def upload_asset(self, repo, release_id, files = None, file_name = None, file_path = None):
        if files:
            fields = [('access_token', self.token)]
            idx = 1
            for file_path in files:
                file_path = file_path.strip()
                if not os.path.isfile(file_path):
                    raise ValueError('file_path not exists: ' + file_path)
                self.delete_exist_file(repo, release_id, os.path.basename(file_path))
                file = ('file', (os.path.basename(file_path), open(file_path, 'rb'), 'application/octet-stream'))
                idx = idx + 1
                fields.append(file)
        elif file_name and file_path:
            self.delete_exist_file(repo, release_id, os.path.basename(file_name))
            fields = {
                'access_token': self.token,
                'file': (file_name, open(file_path, 'rb'), 'application/octet-stream'),
            }
        else:
            raise ValueError('files or (file_name and file_path) should not be False at the same time')
        m = MultipartEncoder(fields=fields)
        url = f"https://gitee.com/api/v5/repos/{self.owner}/{repo}/releases/{release_id}/attach_files"
        response = requests.post(url, data=m, headers={'Content-Type': m.content_type})
        # print(response.text)
        res = response.json()
        if response.status_code < 200 or response.status_code > 300:
            return False, res["message"] if "message" in res else f"Response status_code is {response.status_code}"
        
        if "browser_download_url" in res:
            return True, res["browser_download_url"]
        else:
            return False, "No 'browser_download_url' in response"

def get(key):
    val = os.environ.get(key)
    if not val:
        raise ValueError(f'{key} not set in the environment')
    return val


def get_release_body():
    body_file = os.environ.get('gitee_release_body_file')
    if body_file:
        if not os.path.isfile(body_file):
            raise ValueError('gitee_release_body_file not exists: ' + body_file)
        with open(body_file, 'r', encoding='utf-8') as f:
            return f.read()
    return os.environ.get('gitee_release_body')
    
def set_result(name, result):
    print("result: ", f"{name}={result}")
    github_out = os.environ.get("GITHUB_OUTPUT")
    if github_out:
        with open(github_out, 'a', encoding='utf-8') as output:
            if not '\n' in str(result):
                output.write(f"{name}={result}\n")
                print(f"{name}={result}\n")
            else:
                delimiter = 'EOF'
                output.write(f"{name}<<{delimiter}\n{result}\n{delimiter}\n")
                print(f"{name}<<{delimiter}\n{result}\n{delimiter}\n")
                
def upload_assets(gitee_files, gitee_client, gitee_repo, gitee_release_id):
    result = []
    uploaded_path = set()
    upload_tasks = []
    
    # Collect all files to upload
    for file_path_pattern in gitee_files:
        file_path_pattern = file_path_pattern.strip()
        recursive = True if "**" in file_path_pattern else False
        files = glob.glob(file_path_pattern, recursive = recursive)
        if len(files) == 0:
            raise ValueError('file_path_pattern does not match: ' + file_path_pattern)
        for file_path in files:
            if file_path in uploaded_path or os.path.isdir(file_path):
                continue
            upload_tasks.append((os.path.basename(file_path), file_path))
            uploaded_path.add(file_path)
    
    # Upload files using thread pool
    max_workers = min(4, len(upload_tasks)) if upload_tasks else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(gitee_client.upload_asset, gitee_repo, gitee_release_id, file_name=file_name, file_path=file_path): (file_name, file_path)
            for file_name, file_path in upload_tasks
        }
        
        for future in as_completed(future_to_file):
            file_name, file_path = future_to_file[future]
            try:
                success, msg = future.result()
                if not success:
                    raise Exception(f"Upload file asset failed for {file_name}: {msg}")
                result.append(msg)
            except Exception as exc:
                raise Exception(f"Upload file {file_name} generated an exception: {exc}")
    
    return result
    
def create_release():
    gitee_owner = get('gitee_owner')
    gitee_token = get('gitee_token')
    gitee_repo = get('gitee_repo')
    gitee_tag_name = get('gitee_tag_name')
    gitee_release_name = get('gitee_release_name')
    gitee_release_body = get_release_body()
    gitee_target_commitish = get('gitee_target_commitish')
    
    gitee_files = os.environ.get('gitee_files')
    if gitee_files:
        gitee_files = gitee_files.strip().split("\n")
    else:
        gitee_file_name = os.environ.get('gitee_file_name')
        gitee_file_path = os.environ.get('gitee_file_path')
        if (gitee_file_name and not gitee_file_path) or (gitee_file_path and not gitee_file_name):
            raise ValueError('gitee_file_name and gitee_file_path should be set together')
        if gitee_file_path and not os.path.isfile(gitee_file_path):
            raise ValueError('gitee_file_path not exists: ' + gitee_file_path)
    
    gitee_client = Gitee(owner = gitee_owner, token = gitee_token)
    success, release_id = gitee_client.create_release(repo = gitee_repo, tag_name = gitee_tag_name, name = gitee_release_name, 
                body = gitee_release_body or '-', target_commitish = gitee_target_commitish)
    if success:
        print(release_id)
        if gitee_files:
            upload_assets(gitee_files, gitee_client, gitee_repo, release_id)
        elif gitee_file_path:
            success, msg = gitee_client.upload_asset(gitee_repo, release_id, file_name = gitee_file_name, file_path = gitee_file_path)
            if not success:
                raise Exception("Upload file asset failed: " + msg)
        set_result("release-id", release_id)
    else:
        raise Exception("Create release failed: " + release_id)

def upload_asset():
    gitee_release_id = get('gitee_release_id')
    gitee_owner = get('gitee_owner')
    gitee_repo = get('gitee_repo')
    gitee_token = get('gitee_token')
    gitee_release_body = get_release_body()
    gitee_release_name = os.environ.get('gitee_release_name')
    
    gitee_client = Gitee(owner = gitee_owner, token = gitee_token)
    
    # Convert string release_id to int if needed
    if isinstance(gitee_release_id, str):
        try:
            gitee_release_id = int(gitee_release_id)
        except ValueError:
            # If not a valid integer string, treat it as tag_name or name and get the id
            success, id_or_msg = gitee_client.get_release_id_by_tag(gitee_repo, gitee_release_id)
            if success:
                gitee_release_id = id_or_msg
                print(f"Found release id: {gitee_release_id}")
            else:
                print(f"Release '{gitee_release_id}' not found, creating a new release")
                gitee_release_name = os.environ.get('gitee_release_name', gitee_release_id)
                gitee_target_commitish = os.environ.get('gitee_target_commitish', 'master')
                success, id_or_msg = gitee_client.create_release(
                    repo = gitee_repo,
                    tag_name = gitee_release_id,
                    name = gitee_release_name,
                    body = gitee_release_body or '-',
                    target_commitish = gitee_target_commitish,
                )
                if not success:
                    raise Exception("Create release failed: " + id_or_msg)
                gitee_release_id = id_or_msg
                print(f"Created release id: {gitee_release_id}")

    # Update release body if provided
    if gitee_release_body:
        success, msg = gitee_client.update_release(
            gitee_repo,
            gitee_release_id,
            gitee_release_body,
            name=gitee_release_name,
        )
        if not success:
            raise Exception("Update release body failed: " + msg)
        print(f"Release body updated successfully")
        
    gitee_files = os.environ.get('gitee_files')
    
    if gitee_files:
        gitee_files = gitee_files.strip().split("\n")
        result = upload_assets(gitee_files, gitee_client, gitee_repo, gitee_release_id)
        set_result("download-url", '\n'.join(result))
    else:
        gitee_file_name = os.environ.get('gitee_file_name')
        gitee_file_path = os.environ.get('gitee_file_path')
        if gitee_file_name and gitee_file_path:
            if not os.path.isfile(gitee_file_path):
                raise ValueError('gitee_file_path not exists: ' + gitee_file_path)
            success, msg = gitee_client.upload_asset(gitee_repo, gitee_release_id, file_name = gitee_file_name, file_path = gitee_file_path)
            if not success:
                raise Exception("Upload file asset failed: " + msg)
            set_result("download-url", msg)
        
if __name__ == "__main__":
    gitee_release_id = os.environ.get("gitee_release_id")
    # print("gitee_release_id: ", gitee_release_id)
    if gitee_release_id:
        upload_asset()
    else:
        create_release()
