# iOS 12 兼容构建说明

本仓库在 Venera **v1.4.6**（Flutter 3.32.6，最后一个仍支持 iOS 12 的稳定版）基础上做了以下改动，
使官方云构建（GitHub Actions / Xcode 16.x）产出的未签名 IPA 可以安装运行在 iOS 12.5.8 设备上。

## 改动清单

1. `ios/Runner.xcodeproj/project.pbxproj`
   - 三处 `IPHONEOS_DEPLOYMENT_TARGET` 由 `14.0` 降为 `12.0`
   - Runner 三个构建配置增加 `ALWAYS_EMBED_SWIFT_STANDARD_LIBRARIES = YES`
     （iOS 12 系统内置 Swift 运行时过旧，需要把新版 Swift 运行时打进 App）

2. `ios/Podfile`
   - `platform :ios, '13.0'` → `'12.0'`
   - `post_install` 中强制所有 Pod 目标的部署目标为 `12.0`
     （覆盖 zip_flutter 等 podspec 中写死的 13.0）

3. `ios/Runner/AppDelegate.swift`、`ios/Runner/DirectoryPicker.swift`
   - `UIDocumentPickerViewController(forOpeningContentTypes:)`（iOS 14+，且 UTType 框架
     在 iOS 12 上不存在）加 `if #available(iOS 14, *)` 守卫
   - iOS 12 分支回退到旧 API `UIDocumentPickerViewController(documentTypes: [kUTTypeFolder as String], in: .open)`
   - `directoryURL`（iOS 13+）加可用性守卫

4. `.github/workflows/ios12.yml`（新增）
   - 使用 Xcode 16.x + Flutter 3.32.6 + Rust（aarch64-apple-ios），runner 用
     `macos-15-intel`（arm64 免费队列拥塞，排队 15 分钟会被自动取消）
   - 向 Cargo 写入 target-specific rustflags：
     `[target.aarch64-apple-ios] rustflags = ["-C", "deployment-target=12.0"]`
     把 rhttp（Rust 静态库）的最低系统版本从工具链默认的 13 压到 12
   - `flutter pub get` 后在 pub cache 中把 zip_flutter 的 podspec 平台从 13.0 降到 12.0
     （CocoaPods 解析器在 post_install 之前就会拒绝声明 13.0 的 pod）
   - 运行 `ios12_patches/patch_zip_flutter.py`：把 zip_flutter 0.0.12 的
     `src/miniz.h` 中基于 C++17 `std::filesystem`（path/status/file_size/
     last_write_time，这些 libc++ 符号 iOS 13 才提供）的 `_stat()` 助手，
     在 Apple 平台替换为等价的 POSIX `lstat()`（`<sys/stat.h>`）实现；
     非 Apple 平台保持原样
   - `flutter build ios --release --no-codesign` 后手工打包成 IPA
   - 打包后自动校验每个二进制的 minos、fixup 格式和 Swift 运行时嵌入情况

## 产物

Actions 运行完成后，在工作流运行页面下载 artifact：`venera-ios12-ipa`（未签名 IPA）。
IPA 需在 Windows 上用 Sideloadly（免费 Apple ID 自签名）安装到 iOS 12.5.8 设备。

## 已知限制

- 免费 Apple ID 签名 **7 天后失效**，需要重新安装；最多同时装 3 个自签名 App。
- 目录选择等极少数功能在 iOS 12 上走旧系统 API。
- v1.4.6 比最新版功能略少，但这是能在 iOS 12 上运行的最新版本（Flutter 3.35 起官方彻底移除 iOS 12 支持）。
