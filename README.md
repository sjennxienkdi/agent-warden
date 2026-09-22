# agent-warden

**本地部署的 vibe coding agent 行为审计器（v0 原型）** — 用一个不出网的小模型，看住那些拥有你整台机器权限的 AI 编程助手。

> A locally-deployed behavior auditor for AI coding agents — an offline small model that watches the watchers.

---

## 为什么做这个

2025–2026 年，AI 编码 agent（Claude Code / ZCode / Cursor / Trae / Qoder / WorkBuddy 这类）从补全工具变成了全权代理：读整个仓库、执行 shell、访问网络、推送 git。而已经记录在案的公共事件说明，它们的**后台行为**并不总是与用户预期一致（全部为讨论式引用，含厂商回应，详见 [`docs/incidents.md`](docs/incidents.md)）：

| 时间 | 事件 | 一句话 |
|---|---|---|
| 2026-09 | ZCode 静默快照上传 | 后台加密打包全量 git 历史上传 OSS，失败重试 564 次（官方致歉） |
| 2026-07 | Grok Build CLI 整仓上送 | 会话启动即上传整仓 + 完整 git 历史，实测传输量约为任务所需的 27,800× |
| 2025-08 | Nx 供应链攻击 | 恶意 npm 包武器化 AI agent 外传凭据 |
| 2025-07 | Trae 遥测风波 | 关闭遥测开关后仍上报设备数据（官方否认） |

现有方案的结构性问题：**云端审计平台**要求你把代码流量交给另一家云厂商——监控者成为新的暴露面；**静态规则**分不清 agent 的合法高危行为（装依赖、push、把代码发给模型 API）与真实外传。判别信号不是「发了什么」，而是「**发去哪 / 发多少 / 藏不藏**」。

agent-warden 的位置：**开源 + 本地部署 + 微调小模型**——传感器只读本机出站元数据，推理全程离线，看门人自己不是漏点。

## 这个仓库现在有什么（v0，诚实清单）

**✅ 已完成并实测：**

- **八类攻击分类学 + 六类硬负例分类学**（[`plan.md` §2.4/§2.5](plan.md)）——含三个基于真实事件逆向的变体族（`zcode_style_snapshot` / `grok_style_fullsync` / `poisoned_task_instruction`）；
- **判决模型 practice-v0**（Qwen3-4B QLoRA SFT）：输入 10–40 条事件组成的窗口（shell/文件/网络/git 调用摘要），输出结构化 JSON 判决 `{risk, behavior_class, evidence_events, confidence}`。在合成验证基准上 78/78（JSON 合法率 / 三分类 / 八类精确分类 / 硬负例零误报）——**这是管线验证数字，非泛化能力声明**（见下方诚实声明）；
- **三家主流编程助手的本地取证记录**（腾讯 WorkBuddy / 阿里 Qoder / 字节 Trae 的端点清单与日志行为，[`docs/canary_protocol.md` §9](docs/canary_protocol.md)）；
- **金丝雀测试协议**（[`docs/canary_protocol.md`](docs/canary_protocol.md)）：本地 DNS 前置 + SNI + 体量比的三层观测设计，含合法性边界与负责任披露流程；
- **全流程云复现手册**（[`scripts/practice0/README.md`](scripts/practice0/README.md)）：环境→数据→训练→评测实测 **40 分钟、约 ¥0.9**（3090 实例）。

**🚧 路线图（M1–M7，详见 [`plan.md` §10](plan.md)）：** 本机传感器三路采集（会话日志/出站采样/git 钩子）→ 真实良性数据 + 攻击注入引擎（8 类 × 60 变体、宿主域名 train/test 零共享）→ GRPO（奖励：类别命中/证据 IoU/误报惩罚，全程机器可判）→ 冻结 test600 六 run 评测 → GGUF 本地部署（`warden audit` / `warden watch` 两模式，零出网）。

## 快速开始（复现 v0 训练）

```bash
git clone https://github.com/sjennxienkdi/agent-warden && cd agent-warden
bash scripts/practice0/setup_env.sh        # uv venv + torch cu124 + 全家桶（Linux/macOS/WSL）
.venv/bin/python scripts/practice0/gen_data.py --out data/practice0   # 10 秒重生成数据集（SEED 固定）
.venv/bin/python scripts/practice0/train_sft.py --subset 20 --max-len 2560 --out models/smoke  # 冒烟
.venv/bin/python scripts/practice0/train_sft.py --max-len 2560 --epochs 2 --out models/practice-v0
.venv/bin/python scripts/practice0/quick_eval.py --n 78
```

权重走 `HF_ENDPOINT=https://hf-mirror.com` + `HF_HUB_DISABLE_XET=1`（国内网络必带，原因见手册教训表）。3090 全流程约 40 分钟；消费级显卡 ≥16GB 可跑，8GB 需降 `--max-len`。

## 仓库结构

```
plan.md                       # 实施计划（冻结名册/验收线/红线，v1.1）
docs/
  canary_protocol.md          # 跨 agent 金丝雀测试协议（v0.2）+ 三家取证记录
  incidents.md                # 事件库（带日期/来源/官方回应/置信度分级）
scripts/practice0/            # v0 数据生成 / QLoRA 训练 / 评测 / 云复现手册
data/practice0/               # 合成验证数据集（SEED=20260922，可复现）
results/practice/             # v0 评测结果（隔离区：practice 数字永不进正式报告）
models/                       # 训练产物（gitignore；adapter 见 Releases 说明）
```

## 诚实声明（先读这个再看数字）

1. **78/78 是同分布合成基准上的管线验证**：训练与验证集出自同一套模板生成器（仅参数不同），模型可以通过模板特征拿满分。真实的泛化评测在 M2 冻结 test600 之后，数字出来前本项目**不对外做任何能力声明**。
2. `confidence` 字段未校准，仅作排序参考，不是概率。
3. v0 不做实时阻断，输出是「风险分级 + 证据事件」，不是「已被入侵」的定性。
4. 只监控**本人授权的本机会话**；监控产生的原始日志不入库（脱敏规则见 plan §4.1）。
5. 本项目不能替代 EDR / 企业安全方案；胜负口径限定「八类注入攻击分类学 + 良性误报率 + 本地成本」。

## 合规与隐私

- 传感器全部只读；推理与 watch 全程零出网（正式版将有机械断言测试）；
- 事件库中的厂商条目均为讨论式引用并附官方回应；本项目自己的金丝雀研究若发现阳性，按[披露预承诺](docs/canary_protocol.md)先私下披露厂商、给修复窗口，之后才公开；
- 仅供安全研究与教育用途。

## License

[MIT](LICENSE)
