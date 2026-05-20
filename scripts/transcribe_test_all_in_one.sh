#!/bin/bash

input=$1

python scripts/transcribe.py -i $input -d mps -sc -wts
python scripts/transcribe.py -i $input -d mps -sc -wts --model-path ./checkpoints/Qwen3-ASR-1.7B