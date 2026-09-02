# Apple M macOS VM 离线准备包

这个目录只是一套**离线材料仓和导入模板**，不是已经可用的 macOS 虚拟机。

当前锁定的 QEMU `vmapple` 上游流程要求从一台 Apple Silicon Mac 上已经通过
Virtualization.framework 安装完成的 macOS 12.x VM 导出以下四项：

1. `AVPBooter.vmapple2.bin`
2. `aux.img`
3. `disk.img`
4. `macosvm.json`（包含与上述磁盘配套的 machineId/ECID）

本包已从 Apple CDN 保存一份 macOS Tahoe 26.6 UniversalMac restore IPSW，位置为
`assets/apple/installers/macos-26.6/`。它可供 Apple Virtualization.framework 从本地介质
安装，但当前锁定的 Linux/QEMU `vmapple` 代码并未证明能直接使用它。

运行当前 QEMU 路径仍需从合法的 Apple Silicon VM 导出配套文件。把这些原始文件放入
`assets/apple/incoming/`，然后只在隔离测试 VM 内执行：

```bash
python3 scripts/extract-ecid.py assets/apple/incoming/macosvm.json \
  assets/apple/ready/ecid.txt
scripts/trim-aux.sh assets/apple/incoming/aux.img \
  assets/apple/ready/aux.img.trimmed
cp assets/apple/incoming/AVPBooter.vmapple2.bin assets/apple/ready/
cp assets/apple/incoming/disk.img assets/apple/ready/
python3 scripts/preflight-assets.py
```

## 目录内容

- `assets/apple/installers/`：Apple CDN 的 macOS 26.6 UniversalMac restore IPSW。
- `assets/apple/incoming/`、`ready/`：配套 Apple Silicon VM 资产导入槽，当前为空。
- `bin/`：已在 Ubuntu 24.04 x86_64 隔离 VM 内构建的 QEMU AArch64 二进制。
- `images/linux/`：用于重建隔离测试环境的 Ubuntu 24.04 官方 cloud image。
- `packages/ubuntu-24.04-amd64/`：构建、TCG、Vulkan 开发和 VM 工具的离线 DEB 集合。
- `sources/`：MacVM 代码及锁定上游源码快照。
- `config/`：资源受限的 TCG 启动配置示例。
- `scripts/`：资产转换、预检、哈希验证和启动模板。
- `inventory/`：版本、包列表、动态库和 SHA-256 清单。

## 已验证与未验证

已验证：在 2 vCPU、8 GiB 的 Ubuntu 24.04 x86_64 测试 VM 内，69 个单元测试通过，
QEMU 11.0.93 可编译，`vmapple` 可注册并在 `-S` 状态完成 QMP 初始化。

未验证：macOS 启动、Apple CPU 差异、GPU/PVG、Vulkan、Metal、WindowServer 和性能。
宿主机没有 NVIDIA RTX 4060，因此本包不包含 NVIDIA 驱动，也没有进行 GPU 测试。

## 安全规则

严禁直接在生产宿主机运行构建、安装、测试或本目录的 VM 启动脚本。宿主机只保存
材料。`scripts/launch-vmapple-tcg.sh` 要求显式设置 `MACVM_TEST_VM_CONFIRMED=YES`，并且
默认限制为 2 vCPU / 8 GiB，硬上限 4 vCPU / 16 GiB。

在一台全新的 Ubuntu 24.04 amd64 隔离 VM 中，可先安装离线构建依赖：

```bash
export MACVM_TEST_VM_CONFIRMED=YES
scripts/install-offline-debs.sh
```

离线包严格绑定 Ubuntu 24.04 amd64，不应安装到当前 Ubuntu 26.04 生产宿主机。
