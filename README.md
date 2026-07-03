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
| `*-bypass.img.gz` | 自用旁路由包 | 4096 MiB | 在 `plus` 基础上追加 `files/bypass` 首启配置 |

`bypass` 是维护者自用旁路由配置包，会把网络改为 `10.11.11.3/24`。其他用户请使用标准包或 `plus` 包，不要刷 `bypass` 包。

## 内置包

标准包保持精简，不额外添加常用包。

`plus` 和 `bypass` 当前额外内置：

- `luci-theme-argon`
- `luci-app-argon-config`
- `luci-app-wol`
- `luci-app-openvpn-server`

后续常用包放在 [packages/plus.txt](packages/plus.txt)，只属于旁路由模式的包放在 [packages/bypass.txt](packages/bypass.txt)。

## 默认登录信息

标准包和 `plus` 保持默认管理地址和官方默认密码行为。

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

## 旁路由配置

旁路由首启脚本位于 [files/bypass/etc/uci-defaults/99-bypass-router](files/bypass/etc/uci-defaults/99-bypass-router)，只会进入 `bypass` 固件，不会进入标准包或 `plus` 包。

脚本会设置：

- WAN 静态 IP：`10.11.11.3/24`
- 网关：`10.11.11.1`
- DNS：`10.11.11.1 119.29.29.29`
- 关闭 LAN DHCP
- WAN zone 放行 input/forward
- 时区：`Asia/Shanghai`
- 开启 IPv4 forwarding

脚本不会修改 root 密码。

## 自动构建

GitHub Actions 每周五北京时间 09:20 自动运行一次，并发布到 Releases。

也可以在 Actions 页面手动运行 **Build ImmortalWrt OEC-turbo**：

- `version`：留空时自动使用 ImmortalWrt 最新稳定版本。
- `variants`：默认 `all`，可填 `base`、`plus`、`bypass` 或空格/逗号分隔组合。
- `extra_packages`：临时追加到 `plus` 和 `bypass` 的包。
- `publish_release`：是否发布到 GitHub Releases。
- `prerelease`：是否标记为预发布。

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

第一次从原厂系统刷入第三方系统通常需要拆机短接进入刷机模式。以后再次刷机，一般可以按住 `RESET` 孔后连接数据线进入刷机模式。

不用接电源，Type-C 刷机线本身可以供电。注意要接盒子的 Type-C 口，不是普通 USB 口。

![OEC-turbo 短接点](docs/images/oect-short-point.png)

![OEC-turbo Type-C 口](docs/images/oect-typec-port.png)

![OEC-turbo 主板示意](docs/images/oect-board-overview.png)

### Windows 刷机

1. 安装 RKDevTool 里的驱动，打开 RKDevTool。
2. 准备 Type-C 数据线，一头接 OEC-turbo，另一头接电脑。
3. 不接电源，用镊子等金属工具短接上图两个点。
4. 保持短接时插入电脑，大约 2 秒后电脑提示有设备接入，再松开短接点。
5. 查看 RKDevTool 提示当前是 `MaskROM` 还是 `Loader`。

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

短接并插入电脑后，查看设备：

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

部分 OEC-turbo 底包的 u-boot 里可能使用相同 MAC 地址，例如 `00:15:18:01:81:31`。同一局域网多台设备 MAC 相同会冲突，需要后续修改。

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
