# tavily-exa-router

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README_EN.md) | 简体中文

独立项目,与 Tavily、Exa Labs 无隶属、合作或背书关系。"Tavily" 与 "Exa" 分属其各自所有者的商标。

一个教 AI 编码助手**在任何查询面前选对搜索 API——Tavily 还是 Exa——并正确配置参数**的 agent skill。全部路由规则来自 2026 年 8 月的对标实测和约 40 个带引用的社区来源,见 [`references/evidence.md`](references/evidence.md)。

## 为什么需要

Tavily 和 Exa 的重叠远比想象中少(20 查询实测中,单查询结果域重合度 Jaccard 仅约 22%)。它们是互补关系,分工清晰:

| 能力 | Tavily | Exa |
|---|---|---|
| 社区/论坛内容(Reddit、HN、Quora) | **强** | 弱 |
| 一手官方来源与公告 | 弱 | **强** |
| 学术内容 | 一般 | **强**(arxiv 密集) |
| 非英文内容(如中文)质量 | 参差 | **强** |
| 结果带发布日期 | 几乎没有 | **约 52% 结果携带** |
| 结果带相关性评分 | **始终携带** | 没有 |
| 免读链接直接出 LLM 答案 | **内置** | 经 `outputSchema` 实现 |
| 结构化 JSON 输出 | — | **内置** |
| 抓取已知 URL | **`/extract` 可用** | 基本不可用(实时抓取) |
| 基础查询成本 | 约 $0.008 | 约 $0.007 |

本 skill 把这些编码为:10 秒路由表、模式选择规则(包括哪些"fast"模式**实测反而更差**、应当避开)、参数配方,以及坑清单(废弃参数、`category=company` + 日期过滤的 400 错误、内容计费陷阱等)。

适合当你想要一个轻量、可检查的路由器——它的建议绑定可复现的实测数据,而非厂商传说。它是一个路由启发式,**不是**通用搜索质量基准:只处理一次性公网检索,并明确拒绝监控任务、私有源搜索、URL 安全判定和实时价格查询。

## 安装

1. 获取 API key —— [Tavily](https://app.tavily.com)(免费:每月 1,000 credits)和 [Exa](https://dashboard.exa.ai)(免费:注册送 $20 + 每月 $10)——并导出为环境变量(skill 读取这两个变量):

   ```bash
   export TAVILY_API_KEY=tvly-...
   export EXA_API_KEY=...
   ```

2. 把 skill 装进你所用运行时的 skills 目录:

   | 运行时 | 命令 |
   |---|---|
   | Claude Code | `git clone https://github.com/yk4464/tavily-exa-router.git ~/.claude/skills/tavily-exa-router` |
   | Codex | `git clone https://github.com/yk4464/tavily-exa-router.git ~/.codex/skills/tavily-exa-router` |
   | Gemini CLI | `gemini skills install https://github.com/yk4464/tavily-exa-router.git` |
   | 其他 | 把文件夹拷进你的工具的 skills 目录(不少工具也读 `~/.agents/skills/`) |

   Windows 下对应目录为 `%USERPROFILE%\.claude\skills\` 等。装完重启 agent。路径核对于 2026-08,如你的运行时不同,请查其 skills 文档。

无需记忆任何命令:安装后,当 agent 需要联网搜索且 API key 就绪时,skill 自动加载。

注意:两家控制台和 API 在部分网络环境下可能无法直连(中国大陆通常需要代理,见[社区反馈](references/community-feedback.md))。价格、配额、免费额度和产品行为均为 2026-08 核实的时效快照——生产流量预算请以厂商当前页面为准。

## agent 会得到什么

`SKILL.md` 在需要联网搜索时加载,给 agent:

1. **路由表** —— 13 类任务 → 服务 + 精确参数
2. **模式规则** —— Tavily `basic`/`advanced`(永远别用 `fast`);Exa `auto`(以及何时值得开 `deep-lite`)
3. **范围边界** —— 一次性公网检索之外的活(监控、私有源、URL 安全、实时价格)明确拒绝并给出替代方向
4. **抓取指南** —— 已知 URL 用 Tavily `/extract`,包括哪些站点类型会拦它
5. **坑清单** —— 7 条实测或对照厂商文档验证的陷阱

深度参数表和配方在 `references/` 中按需加载。

## 仓库结构

```
tavily-exa-router/
├── SKILL.md              # skill 本体(路由规则)
├── README.md(中文,主)/ README_EN.md(English)
├── MAINTENANCE.md        # 如何重测、刷新证据、升版本
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE               # MIT
├── tests/                # 证据再生工具包(纯标准库 Python)
│   ├── README.md         # 每个脚本测什么 + 单次成本
│   ├── smoke_test.py     # 廉价漂移检查(约 $0.03),CI 使用
│   └── *.py              # 批量/模式/功能/速度/抓取测试
├── .github/workflows/    # 月度漂移检测 CI(配置 secrets 后激活)
└── references/
    ├── tavily.md         # Tavily 完整参数、端点、配方、定价
    ├── exa.md            # Exa 完整参数、contents 选项、outputSchema、定价
    ├── evidence.md       # 每条规则背后的实测数据
    └── community-feedback.md  # 约 40 个带引用的社区口碑(HN、Reddit、linux.do)
```

## 维护与更新

证据会腐烂(涨价、反爬变化、参数废弃),所以仓库自带测试工具包:`references/evidence.md` 里的每个数字都可以通过 `tests/` 的脚本重新生成。月度 GitHub Actions 漂移检查会在文档事实失效时报警。节奏、刷新流程和 semver 规则见 [`MAINTENANCE.md`](MAINTENANCE.md)(英文)。

## 致谢

路由规则来自两家 API 的正面对比测试(质量、延迟、模式、功能、反爬抓取、成本),以及 HN、Reddit 和中文开发者论坛的社区反馈。测试日期:2026-08-17。

## 许可

[MIT](LICENSE)
