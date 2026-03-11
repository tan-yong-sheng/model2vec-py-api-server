import os
import json


class Meta:
    def __init__(
        self,
        model_path: str,
    ):
        if os.path.exists(f"{model_path}/config.json"):
            with open(f"{model_path}/config.json", "r") as f:
                self.config = json.loads(f.read())
        else:
            self.config = {"model_path": model_path}

    def get(self):
        return self.config
