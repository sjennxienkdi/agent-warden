# practice-v0 微调交接说明

> **✅ 已于 2026-09-22 深夜在 gpushare 3090 实例执行完毕**（训练 17 分 05 秒，评测 78/78 全对），
> adapter 与评测结果已拉回本机（`models/practice-v0/`、`results/practice/v0_eval.json`）。
> 本文件保留为可复现运行手册 + 教训库，供正式训练与 reviewer 项目复用。
> 实测全流程账：环境 ~10 min + 权重下载 2 min 14 s + 冒烟 24 s + 训练 17 min + 评测 ~7 min ≈ **40 分钟，¥0.6–0.9**。

## 一、现状快照（都已就绪，等机器）

| 项 | 状态 | 位置 |
|---|---|---|
| 数据集 v0-min | ✅ 524 窗（train 446 / val 78，攻击 216 覆盖八类，含三个事件打底族；SEED=20260922 可复现） | `data/practice0/`（生成器 `gen_data.py` 随时可重造） |
| 训练脚本 | ✅ QLoRA 配方对齐 plan §5.1/5.2（NF4 双量化 / bf16 / LoRA r16α32 全线性 / completion-only loss） | `train_sft.py` |
| 评测脚本 | ✅ JSON 合法率 / risk 命中 / 八类准确率 / 良性误报 | `quick_eval.py` |
| 环境 | ✅ 跨平台安装脚本（幂等） | `setup_env.sh` |
| 权重 | 本机已备 4B + 1.7B（`models/`，gitignore）；云上建议重下（命令见下） | —— |
| 管线验证 | ✅ 冒烟 20 样本全绿（loss 2.665，adapter 正常落盘） | `models/practice-v0-smoke/` |

**隔离纪律（最重要的一条）**：practice 系列的任何数字**只写 `results/practice/`**，
不得进入 `results/metrics/` 正式 run 或 EVALUATION.md。

## 二、云 GPU 运行手册（租到机器后照抄）

前提：Ubuntu 22.04+，3090/4090 24GB，已装 uv（`curl -LsSf https://astral.sh/uv/install.sh | sh`）。
若镜像自带 torch 2.4–2.6 cu121/cu124，跳过 setup_env 第 1 步。

```bash
# 0) 上传代码与数据（不含权重，约 5MB）
rsync -av --exclude models --exclude .venv --exclude 'data/canary/*/raw' \
    ./ user@host:/root/agent-warden/

# 1) 环境（Linux 分支自动生效；torch 步可跳过则注释掉）
cd /root/agent-warden && bash scripts/practice0/setup_env.sh

# 2) 权重（走 hf-mirror；⚠ 必须关 Xet，否则 401——plan §5.5 已记档）
HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 python -c "
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen3-4B-Instruct-2507', local_dir='models/Qwen3-4B-Instruct-2507')"

# 3) 数据（若未随 rsync 带上，10 秒重生成，SEED 固定保证逐字节一致）
.venv/bin/python scripts/practice0/gen_data.py --out data/practice0

# 4) 冒烟（24GB 卡几分钟）
.venv/bin/python scripts/practice0/train_sft.py --subset 20 --max-len 2560 --out models/smoke

# 5) 全量（3090 预计 40–70 分钟；--max-len 2560 覆盖 99.4% 窗口）
.venv/bin/python scripts/practice0/train_sft.py --max-len 2560 --epochs 2 --out models/practice-v0

# 6) 评测 + 拉回产物
.venv/bin/python scripts/practice0/quick_eval.py --n 78 --out results/practice/v0_eval.json
# 拉回：adapter（~200MB）+ results/practice/（几 KB）；训完删实例数据（plan §13.2-4）
```

与 reviewer 合租：同机顺序跑即可，互不干扰（不同数据目录/输出目录）；
reviewer 管线复用本套脚本约 70%（换数据生成器与 verdict schema 即可）。

## 三、本机实测教训（云上直接避开）

| 坑 | 现象 | 解法 |
|---|---|---|
| 3060 6GB 显存边界 | 4B QLoRA 冒烟（20 样本/seq≤2560）能过，全量两次 OOM（seq 2560 与 2048+expandable_segments 均爆） | 24GB 卡无此问题；本机只做推理/部署 |
| transformers 5.x API | `warmup_ratio`→`warmup_steps`；`torch_dtype`→`dtype`（警告）；`apply_chat_template(return_tensors=)` 返回 BatchEncoding 需取 `["input_ids"]` | 脚本已改，云上直接用 |
| huggingface_hub Xet | hf-mirror 下 401（cas-server.xethub.hf.co 不被代理） | `HF_HUB_DISABLE_XET=1` |
| 清华 PyPI 镜像 403 | uv 安装偶发限流 | 换阿里云镜像（脚本已内置） |
| 窗口渲染超预算 | 合成窗口 p50=1595 tok，正式计划 1280 预算只覆盖 17% | practice 用 2560 先跑；**正式 M2 渲染模板必须按 1280 预算重设计**（短 summary、精简字段），对应测试 `test_window_evidence_never_truncated` |

## 四、本机 1.7B 备选（可选，不着急）

如需在本机出「有数字的排练」：`--model models/Qwen3-1.7B --max-len 2048`（1.7B 4-bit 约 1.5GB，
6GB 宽裕，预计 ~1.5h/2epochs）。注意 Qwen3-1.7B 是 hybrid 模型，脚本已带 `enable_thinking=False`
回退逻辑。产物同样只进隔离区。

## 五、产物清单与去向

```
models/practice-v0/adapter     # LoRA adapter（~200MB，拉回本机）
models/practice-v0/train_config.json  # 超参与环境指纹
results/practice/v0_eval.json  # 排练指标（隔离区）
data/practice0/                # 数据集（可由 SEED 重生，不必拉回）
```
