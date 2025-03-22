import os
from huggingface_hub import upload_large_folder

upload_large_folder(
    repo_id="licyk/sdnote",
    repo_type="model",
    folder_path=os.path.join(os.environ.get("WORKSPACE"), "sdnote")
)
