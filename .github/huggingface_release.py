import os
from huggingface_hub import HfApi

api = HfApi()

api.upload_folder(
    repo_id="licyk/sdnote",
    repo_type="model",
    folder_path=os.path.join(os.environ.get("WORKSPACE"), "sdnote")
)
