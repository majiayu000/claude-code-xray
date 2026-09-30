# 发布清单

当前发布目标：

- 所有者与仓库：`majiayu000/claude-code-xray`
- 可见性：公开
- 站点：<https://majiayu000.github.io/claude-code-xray/>
- 内容许可：CC BY 4.0，署名 `© 2026 majiayu000`

创建或推送远程仓库前完成以下校验：

1. 确认 GitHub 所有者与仓库名。
2. 确认仓库是公开还是私有。
3. 选择内容许可证并加入 `LICENSE`。
4. 用最终 GitHub Pages HTTPS 地址重建站点。
5. 运行生成器的普通校验和 `--publish` 发布校验。
6. 人工抽查首页、搜索、返回总索引、PAR-05 与 PAR-06 的公开脱敏版本。
7. 确认仓库中没有 `_runs`、会话记录、数据库、符号链接、硬链接、密钥或本机绝对路径。

只有全部通过后，才创建远程仓库并启用 GitHub Pages。

站点重建并完成上述检查后，在仓库根目录更新 `site.sha256`，并将它与站点变更一起提交：

```bash
python3 - <<'PY'
import hashlib
from pathlib import Path

site = Path("site")
lines = [
    hashlib.sha256(path.read_bytes()).hexdigest()
    + "  " + path.relative_to(site).as_posix() + "\n"
    for path in sorted(site.rglob("*"))
    if path.is_file() and not path.is_symlink()
]
Path("site.sha256").write_text("".join(lines), encoding="utf-8")
PY
python3 -m unittest discover -s tests -v
```

`site.sha256` 使用标准 SHA-256 清单格式，位于部署目录之外，覆盖 `site/` 中所有普通文件，包括隐藏文件和 `site-manifest.json`，避免清单自校验的循环。Pages 门禁要求清单与磁盘文件集合完全一致，逐文件校验摘要，并固定 `base_url` 为 `https://majiayu000.github.io/claude-code-xray/`。更新清单表示接受对应文件内容，应先完成生成器校验与人工检查。
