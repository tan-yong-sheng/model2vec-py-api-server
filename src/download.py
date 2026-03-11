#!/usr/bin/env python3

import os
import sys

from model2vec import StaticModel

MODEL_DIR = "./models"

model_name = os.getenv("MODEL_NAME", None)
if not model_name:
    print("Fatal: MODEL_NAME is required")
    print(
        "Please set environment variable MODEL_NAME to a HuggingFace model name, see https://huggingface.co/models"
    )
    sys.exit(1)

print(f"Downloading model: {model_name}")

model: StaticModel = StaticModel.from_pretrained(model_name, token=None)
model.save_pretrained(MODEL_DIR)

print("Success")
