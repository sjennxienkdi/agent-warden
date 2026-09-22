# 事件库（incidents.md）

> 引用纪律（plan §13.3）：全部为**讨论式引用**——只陈述公开报道与逆向分析所述事实，
> 不断言未经证实的细节；涉及厂商的条目**必须连官方回应一起引**；本库条目按
> L1（回调/抓包证实）/ L2（行为证据）/ L3（媒体报道与本地记录）分级标注本项目视角的置信度。

## 1. ZCode 静默快照上传（2026-09-18）

- **事件**：开发者 ferstar 磁盘清理时发现 `~/.zcode` 占 700MB+，含 313MB 加密快照；
  复盘称快照打包全量 `.git` 历史 + LFS 缓存上传至阿里云 OSS，失败重试多达 564 次，本地日志被清除。
- **官方回应**：智谱致歉，称问题源于 Repo Wiki 功能默认开启，云端生成后即焚、不留存、未用于训练，已完成自查修复。
- **来源（均为公开报道）**：安全内参 [secrss.com](https://www.secrss.com)、华尔街见闻
  [wallstreetcn.com](https://wallstreetcn.com)、虎嗅 [huxiu.com](https://www.huxiu.com)、
  凤凰科技 [tech.ifeng.com](https://tech.ifeng.com)、博客园/知乎用户复盘帖。
- **本项目置信度**：L3（基于公开复盘与报道；加密内容未经独立解密验证）。
- **用途**：变体族 `zcode_style_snapshot` 的行为链蓝本（plan §4.2）。

## 2. xAI Grok Build CLI 整仓上送（2026-07-12）

- **事件**：独立研究者 Cereblab 的抓包级分析（gist《What xAI's Grok Build CLI Actually
  Sends to xAI: A Wire-Level Analysis》）称 Grok Build CLI v0.2.93 在会话启动时上传整仓
  tracked 源码与完整 git 历史至 GCS bucket——与 agent 实际读取内容无关，拒绝读权限的文件
  照样进 bundle；有第三方实测传输量约为任务所需的 27,800 倍。Hive Security 与 Penligent 独立复核。
- **来源**：[hivesecurity.gitlab.io](https://hivesecurity.gitlab.io)、The Verge / The Next Web
  报道（2026-07-14）。
- **本项目置信度**：L2（多来源独立抓包复核，行为证据充分；内容层面未解密）。
- **用途**：变体族 `grok_style_fullsync` 蓝本；「体量比 + 读取相关性」判别信号的来源。

## 3. Nx 供应链武器化 AI 编码 Agent（2025-08-27）

- **事件**：Snyk 逆向报告称八个恶意 Nx / Nx Powerpack npm 包经 postinstall 脚本投递提示注入，
  使 AI 编码 agent 外传环境变量、SSH 密钥与 shell 历史。
- **来源**：[snyk.io](https://snyk.io)、AI Incident Database（Incident 1210：
  [incidentdatabase.ai](https://incidentdatabase.ai)）、Oligo Security
  [oligo.security](https://www.oligo.security)。
- **本项目置信度**：L2（厂商逆向报告 + 独立事件库收录）。
- **用途**：`injected_instruction_follow` 类别与 `poisoned_task_instruction` 变体族蓝本。

## 4. Trae IDE 遥测风波（2025-07-28）

- **事件**：开发者 GitHub 公开流量分析称 Trae IDE（VSCode 魔改）7 分钟约 500 次请求、
  上传约 26MB 设备标识与使用数据，且关闭遥测开关后仍上传。
- **官方回应**：Trae 团队否认"偷跑"，称数据不涉及个人身份信息，仅用于性能分析与功能优化。
- **来源**：[finance.sina.com.cn](https://finance.sina.com.cn)、IT 之家、知乎/CSDN 流量分析帖。
- **本项目置信度**：L3（单方流量分析 + 官方否认，未经第三方复核）。
- **用途**：对照场景（遥测开关有效性）与遥测目的地分类的现实参照。

## 5. Mitiga 毒测试题事件（2026-06-19）

- **事件**：一份伪装成入职编程测试的物料内嵌指令，使开发者的 AI 助手在两分钟内尝试外传云凭据。
- **来源**：[mitiga.io](https://www.mitiga.io)。
- **本项目置信度**：L2（安全厂商案例报告）。
- **用途**：`poisoned_task_instruction` 变体族的第二素材源。

---

**收录规则**：新条目需含（日期 / 一句话事实 / 官方回应如有 / 来源链接 / 置信度分级 / 用途）。
本项目自有金丝雀研究若产出 L1/L2 阳性，须先走完 `docs/canary_protocol.md` §0 的披露流程方可入库。
