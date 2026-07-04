# 本地 APK 包

此目录存放官方 ImmortalWrt 软件源里没有、但需要随固件构建内置的 APK。当前这些包只通过 [../plus.txt](../plus.txt) 进入 `plus` 和 `bypass` 固件，标准包不会包含。

构建流程会在 ImageBuilder 开始打包前，把匹配的 APK 复制到 ImageBuilder 的本地 `packages/` 目录，并让 ImageBuilder 在构建阶段安装，避免开机后再执行 `apk add --allow-untrusted`。源文件名如果使用 `name_version_arch.apk` 形式，复制时会转换为 APK 仓库可取包的 `name-version.apk` 形式。

当前文件：

| 包 | 文件 | 说明 |
| --- | --- | --- |
| `soho-sealhelper` | `soho-sealhelper_2.0.12-r6_aarch64_generic.apk` | 架构相关包，文件名里的架构必须匹配 ImageBuilder 的 `ARCH_PACKAGES` |
| `soho` | `soho_2.0.12-r8_noarch.apk` | 通用 noarch 包 |
| `luci-app-soho` | `luci-app-soho-2.0.12-r22.apk` | LuCI 界面包 |

更新版本时请保持每个包只保留一个 APK 文件；workflow 会检查数量，避免误把旧版本一起打进固件。
