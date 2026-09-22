#!/usr/bin/env bash
# practice-v0 环境一键安装（Windows / Linux 通用，幂等可重跑）
set -e
cd "$(dirname "$0")/../.."

if [ ! -d .venv ]; then
  uv venv .venv --python 3.12
fi
PY=".venv/Scripts/python.exe"
[ -f "$PY" ] || PY=".venv/bin/python"

echo "=== [1/3] torch cu124（云镜像若自带 torch 可跳过本步） ==="
uv pip install --python "$PY" torch --index-url https://download.pytorch.org/whl/cu124

echo "=== [2/3] 训练全家桶（阿里云镜像；清华镜像偶发 403） ==="
uv pip install --python "$PY" --index https://mirrors.aliyun.com/pypi/simple/ \
  transformers peft bitsandbytes datasets accelerate pydantic pyyaml rich typer

echo "=== [3/3] GPU 自检 ==="
"$PY" -c "import torch, transformers, peft, bitsandbytes as bnb; print('CUDA:', torch.cuda.is_available(), '| GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A', '| torch:', torch.__version__, '| transformers:', transformers.__version__, '| bnb:', bnb.__version__)"

echo "=== 环境就绪。训练入口： ==="
echo "  $PY scripts/practice0/train_sft.py --subset 20 --max-len 2048   # 冒烟"
echo "  $PY scripts/practice0/train_sft.py --max-len 2048 --epochs 2   # 全量（24GB 卡可加 --max-len 2560）"
