# ARM Hackintosh / MacVM

在 **x86_64 Linux** 上，通过 **QEMU `qemu-system-aarch64` + TCG** 运行 ARM64 macOS 的实验工程。
不是 `qemu-arm`（ARM32 用户态模拟），也不是直接使用 KVM 执行 ARM 指令。

## 当前真实进度（2026-09-03）

- **当前 Boot120 / B015 正在使用本地 26.6.2／25G83 安装包解包安装，不是重新在线下载。** 同一安装进程已通过服务启动、许可确认和内部目标盘选择，进度以实际日志为准。尚未完成安装、创建用户或验证安装后启动。[当前记录](docs/boot120-install-progress.md) / [重启衔接计划](docs/boot120-installed-handoff-plan.md)。
- 26.6／25G72 IPSW 已复用于恢复启动；后续取得的 25G83 系统负载已本地保留、打包校验并备份，当前重试复用该本地归档。**完整离线安装流程尚未验收**，不能把本地负载复用等同于安装完成或全部鉴权步骤不联网。
- **Boot119 已进入 ARM64 macOS Tahoe 26.6 / 25G72 的真实安装欢迎界面。** 2026-09-03 03:09:33（北京时间）的 QMP 截图包含完整 Tahoe 图案、标题、说明和 Continue 按钮；旧窗口内容残留已不再出现。
- ARM64 XNU、RecoveryOS、WindowServer、语言选择、恢复工具、真实激活与 KeyRecoveryAssistant 均已运行；安装器为 Mach-O arm64，`InstallAssistant` PID 312、`osinstallersetupd` PID 318。版本、哈希、截图和验收边界见 [Boot119 验收记录](docs/boot119-installer-acceptance.md)。**仅通过“进入安装界面”验收，尚未完成磁盘安装或验证安装后启动。**
- 图形路径修复包含无用描述符加载、可写纹理被当成采样纹理、访问分析误认字面量和能力编号错误，并通过独立回归及真实 UI 验证。Boot119 已按用户批准正常关机并完成备份；Boot120 沿用同一 QEMU 构建，将现有安装盘改接内部 Apple virtio，未重新格式化。
- 当前 Vulkan 是隔离 VM 内的 Mesa lavapipe 软件实现；未测试 NVIDIA 4060 Ti，不能据此声称硬件 GPU 性能。
- 495 个 Python 测试（含隔离临时镜像格式化）通过、零跳过；图形新改动使用像素比对及 Vulkan 验证层逐项验收，最新批次见 [BLOCKERS.md](BLOCKERS.md)。
- 已知未完成：双平面纹理、主渲染目标的完整原生格式读回、部分纹理视图、瞬时栅栏超时后的延迟写回义务保留；Reims 全量 Clippy 仍有既存诊断。未声称完整图形兼容。

本次真实安装欢迎界面（QMP 原始画面转 PNG）：

![Boot119 ARM64 macOS Tahoe 安装欢迎界面](evidence/boot119/screen-installer-first.png)

## 目录与备份

| 路径 | 内容 |
|---|---|
| `third_party/` | 验证 VM 实际源码快照，含本项目改动；保留各上游许可证 |
| `patches/` | 已落地的 QEMU / Reims 有序补丁 |
| `scripts/`、`tools/` | 构建、启动、诊断、镜像准备及 QMP 工具 |
| `tests/` | Python 回归测试；Rust 用例在对应第三方源码中 |
| `docs/` | 架构、环境、性能、恢复链研究及历史记录 |
| `backup/` | 备份范围、来源、构建与依赖清单、Release 制品记录 |

本开发分支是**完整源码快照型备份**，第三方源码不是仅有提交号的空子模块。
原始上游锁见 `upstreams.lock.toml`；原 `.gitmodules` 存在 `backup/original.gitmodules`。
不要对已修改的快照重复执行 apply-patches 或强制 submodule update。
备份边界、未上传的大文件及恢复注意事项见 [backup/README.md](backup/README.md)。

## 执行边界

**禁止在本机 Mac 或生产 Ubuntu 宿主机上构建、安装、调试、测试。**
一切执行仅在专用、可丢弃的 Linux x86_64 隔离 VM 内进行，不替换 `/usr` 下的 QEMU、驱动或库，
不改生产 VM、PCI/USB 穿透或服务配置。外层隔离 VM 上限 16 核 / 36 GiB；当前 ARM 客体 8 核 / 16 GiB。

仅在隔离 VM 内：

```bash
export MACVM_DEBUG_ENV_CONFIRMED=YES
./scripts/test.sh
```

`scripts/validation-boot118.sh`、`validation-boot119.sh` 保留历史配置；`validation-boot120.sh` 是当前恢复启动配置，
包含绝对路径并依赖离线恢复材料，不是全新机器的一键安装器。
`scripts/build-graphics-storage-validation.sh` 使用独立新构建目录，保留前一构建并校验其二进制哈希，
仍依赖前一构建的 `config.status`。本次安装界面已单独截图验收，但不代表完整安装或全图形兼容。
重建前先阅读备份清单和 `BLOCKERS.md`，在新路径准备资源，不覆盖原运行目录。
这些脚本不是安装后重启入口，不能在已有运行目录上重新执行。

较早的 Phase 1 首页保留在 [docs/initial-phase1-readme.md](docs/initial-phase1-readme.md)，其中历史状态不能代表当前进度。
