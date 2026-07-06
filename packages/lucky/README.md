# Lucky 本地包

此目录存放 `bypass` 固件内置使用的 Lucky 安装包。

当前文件：

- `lucky_3.0.0_Linux_arm64_xiaojv_waf.tar.gz`

构建流程只使用本地文件，不再从 Lucky 服务器实时下载，避免 GitHub Actions 因网络超时导致 `bypass` 构建失败。

更新 Lucky 时，直接替换同名 tar.gz 文件即可。替换后建议手动运行一次 Actions 的“仅自用旁路由包 + 只生成 Actions Artifacts”进行验证。
