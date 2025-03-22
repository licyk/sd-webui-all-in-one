import os
from modelscope.hub.api import HubApi

api = HubApi()
api.login(os.environ.get("MODELSCOPE_API_TOKEN"))

api.upload_folder(
    repo_id="licyks/sdnote",
    repo_type="model",
    folder_path=os.path.join(os.environ.get("WORKSPACE"), "sdnote")
)
