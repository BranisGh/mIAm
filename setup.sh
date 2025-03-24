#!/bin/bash
uv pip install --no-cache-dir --upgrade pip
uv pip install --no-cache-dir -r requirements.txt
uv pip install --no-cache-dir -e .
