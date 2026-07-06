# OEC-turbo 刷机参考

以下内容整理自 [ophub/amlogic-s9xxx-armbian#2736](https://github.com/ophub/amlogic-s9xxx-armbian/pull/2736) 相关讨论和 ophub OEC-turbo 资料。刷机有风险，请提前准备救砖工具并确认硬件版本。

## 准备文件

- 刷机工具：[RkDevTool_v2.84__DriverAssitant_v5.12.tar.xz](https://github.com/ophub/kernel/releases/download/tools/RkDevTool_v2.84__DriverAssitant_v5.12.tar.xz)
- Loader 文件：
  - [MiniLoaderAll.bin](https://github.com/ophub/u-boot/blob/main/u-boot/rockchip/wxy-oect/MiniLoaderAll.bin)
  - [rk356x-MiniLoaderAll.bin](https://github.com/ophub/u-boot/blob/main/u-boot/rockchip/wxy-oect/rk356x-MiniLoaderAll.bin)
- 拆机视频：[Bilibili BV1vdVzzsErB](https://www.bilibili.com/video/BV1vdVzzsErB/)
- 拆机图文：[CSDN 文章](https://blog.csdn.net/John_Lenon/article/details/146461220)

## 短接点和 Type-C 口

短接通常只在第一次从原厂系统刷入第三方系统时需要。后续再次刷机时，设备保持断电、不插外置电源，按住 `RESET` 孔后插入 Type-C 数据线，一般即可进入刷机模式。

刷机过程全程不用接外置电源，Type-C 刷机线本身可以供电。注意要接盒子的 Type-C 口，不是普通 USB 口。

![OEC-turbo 短接点](images/oect-short-point.jpg)

![OEC-turbo Type-C 口](images/oect-typec-port.jpg)

![OEC-turbo 主板示意](images/oect-board-overview.jpg)

## Windows 刷机

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

![RKDevTool MaskROM 写入示例](images/rkdevtool-maskrom.jpg)

![RKDevTool Loader 写入示例](images/rkdevtool-loader.jpg)

## macOS 刷机

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

![macOS rkdeveloptool 模式示例](images/mac-rkdeveloptool-mode.jpg)

刷写命令：

```sh
# MaskROM 模式需要先写 loader；Loader 模式可跳过这一步。
sudo rkdeveloptool db MiniLoaderAll.bin

# 写入解压后的 img 镜像。
sudo rkdeveloptool wl 0 immortalwrt.img
```

看到 `Write LBA from file (100%)` 即表示写入完成。

![macOS OpenWrt 刷写示例](images/mac-openwrt-flash.jpg)

## MAC 地址提醒

部分 OEC-turbo 底包的 u-boot 里可能使用相同 MAC 地址，例如 `00:15:18:01:81:31`。同一局域网多台设备 MAC 相同会冲突，需要自行修改。

参考 ophub 文档第 `12.7.2.4` 节：[README.cn.md](https://github.com/ophub/amlogic-s9xxx-armbian/blob/main/documents/README.cn.md)

u-boot 环境变量修改示例：

```sh
sudo apt-get update
sudo apt-get install -y libubootenv-tool
sudo fw_setenv ethaddr 02:55:66:77:88:99
sudo fw_printenv ethaddr
```

## OpenWrt 启动截图参考

![OEC-turbo OpenWrt 截图 1](images/oect-openwrt-screenshot-1.jpg)

![OEC-turbo OpenWrt 截图 2](images/oect-openwrt-screenshot-2.jpg)
