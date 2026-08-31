# Claude Code XRY

Claude Code XRY 是一组按独立机制拆开的中文研究页面。每一页围绕一个主要用户动作、一个关键状态转换和一组停止条件，用官方契约与可复现实验互相核对。

当前公开站点包含：

- 50 个已独立验收的核心机制页面
- 已通过同等验收的补充机制页面
- 可搜索的总索引、研究方法说明和逐页导航

生成后的静态站点位于 [`site/`](./site/)。这个仓库只保存经过允许列表筛选和隐私检查的公开内容；原始运行记录、会话、鉴权信息、证据缓存和本机路径不进入这里。

## 本地预览

```bash
python3 -m http.server 5580 --bind 127.0.0.1 --directory site
```

然后打开 <http://127.0.0.1:5580/>。

## 在线站点

GitHub Pages：<https://majiayu000.github.io/claude-code-xray/>

仓库公开发布于 `majiayu000/claude-code-xray`。研究文字与页面内容采用 [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) 许可，署名为 `© 2026 majiayu000`。Anthropic 与 Claude 是其各自权利人的商标；本项目是独立研究项目，与 Anthropic 无隶属或背书关系。

研究源与生成器保存在单独的私有工作目录中，不属于本公开仓库。
