# ImmortalWrt OEC-turbo 自动构建

基于官方 ImmortalWrt `armsr/armv8` rootfs 和 [ophub/amlogic-s9xxx-openwrt](https://github.com/ophub/amlogic-s9xxx-openwrt) 打包链路，为 WXY OEC-turbo 原版设备生成 OpenWrt/ImmortalWrt 固件。

当前默认设备为 `wxy-oect`，对应 ophub 模型库中的 `WXY-OEC-turbo-4g(Original-Edition)`。`wxy-oect-mod` 是换芯片/eMMC 版本，不属于本仓库默认构建目标。

## 重要说明

- 本仓库不是 ImmortalWrt 官方设备适配仓库。
- 官方 ImmortalWrt 目前没有原生 `wxy-oect` 的 `rockchip/armv8` profile。
- 构建流程参考 ophub 的 OEC-turbo 产物：先使用官方 ImmortalWrt `armsr/armv8 generic` rootfs，再通过 ophub/unifreq 的内核、DTB、bootloader 和设备配置打包为 `wxy-oect` 镜像。
- 刷机前请确认设备确实是 OEC-turbo 原版 `wxy-oect`。不同硬件版本混刷可能无法启动。

## 固件变体

同一次构建会发布多个变体。标准包不带特殊后缀，另外两个变体带后缀区分用途。

| 文件名 | 用途 | rootfs 分区 | 内容 |
| --- | --- | --- | --- |
| 无特殊后缀 | 标准包 | 1280 MiB | 官方 ImmortalWrt rootfs 默认包，不写入旁路由配置 |
| `*-plus.img.gz` | 常用包 | 2048 MiB | 在标准包基础上追加 `packages/plus.txt` |
| `*-bypass.img.gz` | 自用旁路由包 | 4096 MiB | 在 `plus` 基础上追加旁路由首启配置和 Lucky |

`bypass` 是维护者自用旁路由配置包，会把管理地址改为 `10.11.11.3/24`。其他用户请使用标准包或 `plus` 包，不要刷 `bypass` 包。

## 内置包

标准包保持精简，不额外添加常用包。

`plus` 和 `bypass` 当前通过包列表额外内置：

- `luci-theme-argon`
- `luci-app-argon-config`
- `luci-app-wol`
- `luci-app-openvpn-server`
- `soho-sealhelper`
- `soho`
- `luci-app-soho`

常用包维护在 [packages/plus.txt](packages/plus.txt)，只属于旁路由模式的包维护在 [packages/bypass.txt](packages/bypass.txt)。

其中 Soho 相关包来自本仓库的 [packages/local-apk](packages/local-apk) 本地 APK。`soho-sealhelper` 是架构相关包，当前构建使用匹配 `armsr/armv8` ImageBuilder 的 `aarch64_generic` 包；`soho` 和 `luci-app-soho` 使用通用包。标准包不会内置这些本地 APK。

`plus` 和 `bypass` 每次构建都会重新内置这些包。通过 LuCI 固件升级页面勾选“保留配置”时，Argon 配置、WOL 配置、Soho UCI 配置和 OpenVPN UCI 配置会随 `/etc/config/` 保留；OpenVPN Server 的证书、补充配置和 Soho 的常见配置目录也会通过 [files/plus/etc/uci-defaults/97-plus-sysupgrade](files/plus/etc/uci-defaults/97-plus-sysupgrade) 写入保留清单，覆盖 `/etc/openvpn/`、`/etc/easy-rsa/pki/`、`/etc/easy-rsa/vars-server`、`/etc/openvpn-addon.conf` 和 `/etc/soho/`。

该补充脚本会在刷入包含它的固件后生效；如果从本仓库早期固件首次升级，且已经手动改过 `/etc/easy-rsa/vars-server` 或 `/etc/openvpn-addon.conf`，升级前请先手动备份这两个文件。

## Lucky 内置说明

只有 `bypass` 固件内置 Lucky，标准包和 `plus` 都不内置。

`bypass` 内置方式尽量贴近 Lucky 官方自动脚本：

- 安装目录：`/etc/lucky.daji`
- 服务脚本：`/etc/init.d/lucky.daji`
- 启动方式：`lucky -c /etc/lucky.daji/lucky.conf`
- 默认后台地址：`http://10.11.11.3:16601/`
- 默认账号和密码：`666` / `666`

构建时会从官方发布地址下载指定版本的 arm64 包并校验 SHA256。`/etc/lucky.daji/` 会写入 `/etc/sysupgrade.conf`，通过 LuCI 固件升级页面勾选“保留配置”时，Lucky 配置和后台升级后的 Lucky 文件会一起保留。

如果通过 RKDevTool 重新整盘刷写 `.img`，设备存储会被覆盖，Lucky 数据不会自动保留；整盘重刷前请先在 Lucky 后台备份配置。

## 默认登录信息

本仓库不写入或修改 root 密码。当前官方 ImmortalWrt `armsr/armv8 generic` rootfs 的 root 密码字段为空，因此当前构建默认为空密码。

| 固件 | 默认管理地址 | 用户名 | 默认密码 |
| --- | --- | --- | --- |
| 标准包 | `http://192.168.1.1/` | `root` | 空密码 |
| `plus` | `http://192.168.1.1/` | `root` | 空密码 |

首次登录后建议立即设置 root 密码。

`bypass` 的默认管理地址为 `http://10.11.11.3/`，用户名 `root`，密码同样保持官方默认空密码。该包仅适用于维护者自己的旁路由环境。

## 分区说明

最终镜像由 ophub 打包器生成，默认包含 boot 分区和 btrfs rootfs 分区。`config/build.env` 中的 `IMMORTALWRT_*_ROOTFS_PARTSIZE` 控制最终镜像 rootfs 分区大小，单位为 MiB。

当前配置：

```ini
IMMORTALWRT_BASE_ROOTFS_PARTSIZE=1280
IMMORTALWRT_PLUS_ROOTFS_PARTSIZE=2048
IMMORTALWRT_BYPASS_ROOTFS_PARTSIZE=4096
```

`bypass` 面向维护者自用的 8G 存储设备，预留 4G rootfs 空间用于长期安装插件和保存运行数据。标准包和 `plus` 不假定用户设备一定有 8G 可用空间。

## 旁路由配置（仅 Bypass 固件）

旁路由首启脚本位于 [files/bypass/etc/uci-defaults/99-bypass-router](files/bypass/etc/uci-defaults/99-bypass-router)，只会进入 `bypass` 固件，不会进入标准包或 `plus` 包。

脚本会设置：

- 静态管理地址：`10.11.11.3/24`
- 双网口环境优先配置 `wan`；单网口环境没有 `wan` 时配置 `lan`
- 网关：`10.11.11.1`
- DNS：`10.11.11.1`、`119.29.29.29`
- 关闭 LAN DHCP
- WAN zone 放行 input/forward
- 时区：`Asia/Shanghai`
- 开启 IPv4 forwarding

脚本不会修改 root 密码。

## 自动构建

GitHub Actions 每周五北京时间 09:20 自动运行一次，并发布到 Releases。

也可以在 Actions 页面手动运行 **Build ImmortalWrt OEC-turbo**：

- `version`：ImmortalWrt 发布版本；留空时自动使用最新稳定版。
- `variants`：选择本次要构建的固件变体，默认“全部变体”。
- `extra_packages`：临时追加到 `plus` 和 `bypass` 的软件包，多个包用空格分隔；一般留空。
- `publish_release`：选择发布到 GitHub Releases，或只生成 Actions Artifacts。
- `prerelease`：选择正式发布或标记为预发布。

## 刷机参考

以下内容整理自 [ophub/amlogic-s9xxx-armbian#2736](https://github.com/ophub/amlogic-s9xxx-armbian/pull/2736) 相关讨论和 ophub OEC-turbo 资料。刷机有风险，请提前准备救砖工具并确认硬件版本。

### 准备文件

- 刷机工具：[RkDevTool_v2.84__DriverAssitant_v5.12.tar.xz](https://github.com/ophub/kernel/releases/download/tools/RkDevTool_v2.84__DriverAssitant_v5.12.tar.xz)
- Loader 文件：
  - [MiniLoaderAll.bin](https://github.com/ophub/u-boot/blob/main/u-boot/rockchip/wxy-oect/MiniLoaderAll.bin)
  - [rk356x-MiniLoaderAll.bin](https://github.com/ophub/u-boot/blob/main/u-boot/rockchip/wxy-oect/rk356x-MiniLoaderAll.bin)
- 拆机视频：[Bilibili BV1vdVzzsErB](https://www.bilibili.com/video/BV1vdVzzsErB/)
- 拆机图文：[CSDN 文章](https://blog.csdn.net/John_Lenon/article/details/146461220)

### 短接点和 Type-C 口

短接通常只在第一次从原厂系统刷入第三方系统时需要。后续再次刷机时，设备保持断电、不插外置电源，按住 `RESET` 孔后插入 Type-C 数据线，一般即可进入刷机模式。

刷机过程全程不用接外置电源，Type-C 刷机线本身可以供电。注意要接盒子的 Type-C 口，不是普通 USB 口。

![OEC-turbo 短接点](docs/images/oect-short-point.png)

![OEC-turbo Type-C 口](docs/images/oect-typec-port.png)

![OEC-turbo 主板示意](docs/images/oect-board-overview.png)

### Windows 刷机

1. 安装 RKDevTool 里的驱动，打开 RKDevTool。
2. 准备 Type-C 数据线，一头接 OEC-turbo，另一头接电脑。
3. 首次从原厂系统刷入时，不接外置电源，用镊子等金属工具短接上图两个点。
4. 保持短接时插入 Type-C，大约 2 秒后电脑提示有设备接入，再松开短接点。
5. 后续再次刷机时，不接外置电源，按住 `RESET` 孔后插入 Type-C，电脑识别到设备后再松开 `RESET`。
6. 查看 RKDevTool 提示当前是 `MaskROM` 还是 `Loader`。

如果是第一次刷机，通常进入 `MaskROM`，需要同时选择 loader 和 img 镜像。如果之前已经刷过 Armbian/OpenWrt，再刷通常进入 `Loader`，只选择 img 镜像即可。

RKDevTool 两行路径示例：

```text
0xCCCCCCCC  LoaderToDDR  <MiniLoaderAll.bin 文件路径>
0x00000000  system       <解压后的 .img 文件路径>
```

镜像要先解压成 `.img`，不要直接刷 `.gz` 压缩包。

![RKDevTool MaskROM 写入示例](docs/images/rkdevtool-maskrom.png)

![RKDevTool Loader 写入示例](docs/images/rkdevtool-loader.png)

### macOS 刷机

安装 Homebrew：

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

安装并编译 `rkdeveloptool`：

```sh
brew install automake autoconf libusb pkg-config git wget
git clone https://github.com/rockchip-linux/rkdeveloptool
cd rkdeveloptool
export CXXFLAGS="-g -O2 -Wno-error=vla-cxx-extension"
autoreconf -i
./configure
make -j $(nproc)
cp rkdeveloptool /opt/homebrew/bin/
```

进入刷机模式后查看设备。首次从原厂系统刷入时通常需要短接；后续再次刷机时，不接外置电源，按住 `RESET` 孔后插入 Type-C 即可。

```sh
rkdeveloptool ld
```

![macOS rkdeveloptool 模式示例](docs/images/mac-rkdeveloptool-mode.png)

刷写命令：

```sh
# MaskROM 模式需要先写 loader；Loader 模式可跳过这一步。
sudo rkdeveloptool db MiniLoaderAll.bin

# 写入解压后的 img 镜像。
sudo rkdeveloptool wl 0 immortalwrt.img
```

看到 `Write LBA from file (100%)` 即表示写入完成。

![macOS OpenWrt 刷写示例](docs/images/mac-openwrt-flash.png)

### MAC 地址提醒

部分 OEC-turbo 底包的 u-boot 里可能使用相同 MAC 地址，例如 `00:15:18:01:81:31`。同一局域网多台设备 MAC 相同会冲突，需要自行修改。

参考 ophub 文档第 `12.7.2.4` 节：[README.cn.md](https://github.com/ophub/amlogic-s9xxx-armbian/blob/main/documents/README.cn.md)

u-boot 环境变量修改示例：

```sh
sudo apt-get update
sudo apt-get install -y libubootenv-tool
sudo fw_setenv ethaddr 02:55:66:77:88:99
sudo fw_printenv ethaddr
```

### OpenWrt 启动截图参考

![OEC-turbo OpenWrt 截图 1](docs/images/oect-openwrt-screenshot-1.png)

![OEC-turbo OpenWrt 截图 2](docs/images/oect-openwrt-screenshot-2.png)
