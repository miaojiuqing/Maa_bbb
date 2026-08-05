<!-- markdownlint-disable MD033 MD041 -->

<p align="center">
  <img alt="LOGO" src="logo.ico" width="256" height="256" />
</p>

<div align="center">

## Maa_bbb

(识宝小助手)

基于MAA框架制作的崩坏三小助手。图像技术 + 模拟控制，解放双手！由 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 强力驱动！

[点击申请加入小助手交流群](<https://qm.qq.com/q/XrFQKgGvaI>)

更多功能敬请期待（提 Issue）

（自动乐土极速画饼中）

**本助手完全免费，没有任何收费的地方。如果你是买来的请举报拉黑商家，同时可以告诉作者是谁在卖。**

</div>
<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB">
  <img alt="license" src="https://img.shields.io/github/license/miaojiuqing/Maa_bbb">
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows-blueviolet">
  <img alt="commit" src="https://img.shields.io/github/commit-activity/m/miaojiuqing/Maa_bbb">
   <a href="https://mirrorchyan.com/zh/projects?rid=Maa_bbb" target="_blank"><img alt="mirrorc" src="https://img.shields.io/badge/Mirror%E9%85%B1-%239af3f6?logo=countingworkspro&logoColor=4f46e5"></a>
</p>

---

## 简介

**Maa_bbb** 是由miaojiuqing（淼九清）开发的游戏自动化工具，旨在帮助玩家完成每日任务，和以后会添加的一些小活动。

**注意：** 本项目推荐使用mumu模拟器(好用)、雷电模拟器，其他模拟器没测过。PC 请设置为16:9分辨率。

[视频链接](<https://www.bilibili.com/video/BV1Ld42z1ERu>)

[点击链接加入群聊](<https://qm.qq.com/q/XrFQKgGvaI>)

点击进入下载界面 [Releases](https://github.com/miaojiuqing/Maa_bbb/releases/)

如果你不知道你应该下载什么版本，请认准 x86_64 字样。

---

## PC端使用须知

### 游戏设定

游戏需在 设置 -> 辅助 中，关闭显示菜单提示

![操作图指引](<https://s21.ax1x.com/2025/10/16/pVqBJde.md.png>)

错误示例

![错误示例](<https://s21.ax1x.com/2025/10/16/pVqBYIH.md.png>)

正确示例

![正确示例](<https://s21.ax1x.com/2025/10/16/pVqBNid.md.png>)

### 命令行与工作排程器

本项目目前使用 [MFW-PyQt6](https://github.com/overflow65537/MFW-PyQt6/releases) 作为前端 GUI 与可执行入口。

命令行使用请参考 MFW-PyQt6 的说明

> MFW 开关写在分隔符 `--` 之前；之后仅传给 Qt。
>
> - `--config-id <ID>`：使用指定配置 ID 启动（可用 `--config-id=<ID>`）
> - `--direct-run`：启动后直接运行任务
> - `--force-restart`：强制启动，会关闭同目录下正在运行的其他 MFW 实例
> - `--dev`：启用调试模式（显示测试页）

在本项目中， config-id 为您所创建的配置在 Maa_bbb 目录下 config/configs 中的文件名，文件名不包含扩展名。

例 ```--config-id c_7a742d90d628484da8e3ee30869b35a6``` 会加载执行 ```config/configs/c_7a742d90d628484da8e3ee30869b35a6.json``` 。

当使用 Windows 工作排程器运行 Maa_bbb 时，不要忘记勾选“使用最高特权执行”。

动作选项卡中，无需填写“起始于”选项。

### 自动战斗

自动战斗(和所有涉及键码输入的)无法使用后台运行功能

自动战斗功能运行战斗时，请一定不要点击键盘上的特殊键(如 Win, Ctrl, Alt 等)，**⚠️否则可能会导致整个电脑界面被各种各样快捷键唤出的窗口占满导致无法操作！！！**
  
若一定需要暂停，请按下ESC进入暂停界面后等待两三秒，这时候再去进行其他操作(正常情况下识别到暂停界面将不会进行任何操作，若想继续战斗点击暂停界面的继续战斗即可)

## 主要功能

**以下任务基本都要游戏处于主界面才能开始运行**

### 启动

- ✅ 启动游戏并自动进入主界面

### 日常

- ✅ 材料远征
- ✅ 家园
  - ✅ 金币领取
  - ✅ 打工
  - ✅ 远征派遣
- ✅ 舰团
  - ✅ 每日委托
  - ✅ 每周活跃奖励
  - ✅ 保税物品申请（我真是闲得慌做这玩意）
  - ✅ 模拟作战室-减负
- ✅ 奖励领取
  - ✅ 日常任务奖励
  - ✅ 日常活跃专领
  - ✅ 凭证任务奖励
  - ✅ 邮件奖励

### 周常

- ✅ 自动超弦空间（老登苦痛一以下无压力）
  - ✅ 自动切换指定编队
  - ✅ 自选战斗逻辑
  - ✅ 是否只打前三层
- ✅ 每周答题-减负
- ✅ 每周分享
- ✅ 冒险委托-减负（话说这算周常还是日常）
  - ✅ 樱色轮回
  - ✅ 后崩坏书1
  - ✅ 后崩坏书2
  - ✅ 天命总部
- ✅ 记忆战场-减负
- ✅ 万象虚境-减负
  - ✅ 层数选择
  - ✅ 副本选择
  - ✅ 是否消耗时序通行证
  - ✅ 挑战次数选择
- ✅ 拓境战幕-减负

### 乐土

- 🚧 往世乐土-周常通关（开发中，目前仅导航至乐土箱庭）
- ✅ 克莱茵打灰（刷装甲等级/乐土币/萌新刷命定歧路）| 自己会找路
  - ✅ 减负模式-无限刷
  - ✅ 浅层序列刷
  - ✅ 首层复刷
  - ✅ 无限刷取模式

### 商店

- ✅ 每日商店选购
  - ✅ 后勤终端
    - ✅ 只购买星石为货币的商品
    - ✅ 只购买金币为货币的商品
    - ✅ 购买所有货币为星石和金币的商品
  - ✅ 每日普通晶体核心购买
- ✅ 每周商店选购
  - ✅ 1星石的虚境挑战书
  - ✅ 吼姆秘藏
- ✅ 每周乐土商店（自选购买商品）
  - ✅ 吼吼休假卷
  - ✅ 相转移镜面
  - ✅ 聚能·空间透镜
  - ✅ 虚境挑战书
- ✅ 虚境商店每周特惠
- ❌ 每月商店选购
- ❌ 每版本商店选购——我感觉这个好像没必要做啊，每个版本相隔的天数都不一样

### 活动

- ✅ 当期活动日常（太难的不做，有PVP元素/会影响其他玩家的不做）
  - ✅ 繁星旅航-每日挑战
  - ✅ 论文危机-收菜
  - ✅ 天命特别教室

### 额外功能

- ✅ 自动战斗（乐土版）
  - ✅ 通用战斗逻辑（开环/开人偶流）
  - ✅ 通用战斗逻辑（禁环/禁人偶流）
  - ✅ 通用战斗逻辑（禁武器技）
  - ✅ 薇塔（开环流）
  - ✅ 崩落符（普攻流）— PC推荐，模拟器不推荐，A太慢了
  - ✅ 嗨♪爱愿妖精（开环流）
  - ✅ 只按武器技（适用于大月下）
  - ✅ 新春虫（开环流）
  - ✅ 花火大招特殊处理
- ✅ 自动战斗pro（新框架，针对单个女武神精细编写）
  - ✅ 真理之律者
  - ✅ 梅比乌斯
  - ✅ 自动切换角色
- 🚧 超弦空间/量子流行版自动战斗（待填坑）
- ✅ 自动过剧情
  - ✅ 纯点击跳过（看到跳过就点，会忽略"今日不再提示"，可能错过CG）
  - ✅ 正常过剧情-手动选择选项（遇到对话选项会停）
  - ✅ 正常过剧情-自动选择选项（自动选第一个）
  - ✅ 古早剧情点击跳过（双悬浮窗那种老的）

## 选择所要使用的 UI

### MFW-PyQt6（当前使用）

- 功能丰富，支持自定义任务流程、每周任务周期执行等
- 下载 [Releases](https://github.com/overflow65537/MFW-PyQt6/releases) 包
- 由 [overflow65537](https://github.com/overflow65537) 开发维护

### MFAAvalonia（已弃用，不与当前CFA冲突）

- 社区 [SweetSmellFox](https://github.com/SweetSmellFox) 编写的基于Avalonia的GUI，内置MaaFramework直接控制任务流程
- 打包自动发版，可满足大部分需求
- [项目地址](https://github.com/SweetSmellFox/MFAAvalonia/)

## 使用模拟器还是 win32

### ADB(模拟器)

- 软件启动后左上角资源选择选择“模拟器”，然后右边检查窗口是否为“下载了崩坏三的模拟器”，模拟器分辨率自行设置为16:9，可以挂后台！

### win32(电脑客户端)

- 软件管理员启动后左上角资源选择选择“桌面端”，然后右边检查窗口是否为“崩坏3”，游戏内窗口自行设置为16:9 (你开全屏分辨率是16:9就能全屏用，不能就乖乖窗口化)，触控与截屏模式默认即可，后台鼠标会闪烁属于正常现象。

## 常见问题

提问前请检查

模拟器:
- 模拟器的分辨率是否为16:9
- 任务名中带“减负”字样的任务你是否解锁减负功能

PC端:
- 左上角的资源选择是否为“桌面端”
- 游戏分辨率是否为16:9
- 游戏辅助菜单是否已关闭(关闭方法在上面)
- 游戏操控方式是否为键鼠(计划后续添加纯键盘自愿选择)
- 软件右上角的窗口选择是否为崩坏3
- 请检查您启动时是否是以管理员方式启动（右键 MFW.exe -> 使用管理员权限运行）
- 请通过截图测试查看当前截图是否正常，若非正常请自行更换截图方式

反馈问题请附上日志文件 `debug/maafw.log`以及问题界面的截图

提示“应用程序错误”，一般是缺少运行库，请尝试安装 [vc_redist](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### QA

> Q:我软件启动之后显示“资源加载失败”怎么办
>
> A1:打开安装目录，删除除了config之外的文件夹，然后下载最新版拖入安装目录，之后再次启动即可
>
> A2:作者搞错了，等更新，一般半小时之内解决
  
> Q:我是XXX渠道服的，我在软件资源列表未寻找到我的渠道服的资源
>
> A:包名给我，手机抓取包名方法为：启动你要抓取包名的崩坏3后，切换后台，设置-应用-找到你刚刚启动的要抓取包名的崩坏3，点进去会显示包名，复制给我就好。如果是模拟器的话，直接进群发送APK文件给我我来抓

> Q:我任务奖励领取功能一直不点是为啥
>
> A:你黑边没关，滑到最上面看一下如何关闭

> Q:怎么导出日志
>
> A:软件内点击|→即可导出日志，若该bug可以稳定复现的话最好导出前删除debug文件夹之后再触发一次bug之后再导出

> Q:我运行了安装目录中的依赖库安装后，软件与cli均双击无法启动，但shift+右键命令行输入./MFAAvalonia.exe可以启动是为什么
>
> A:邪恶的微软犯病了，请右键 MFAAvalonia.exe -> 属性 -> 解除锁定 后再次尝试

## 关于新版mumu模拟器如何连接

近期 MuMu 模拟器 5.0 正在进行内测，并预计将于 6 月 20 日起陆续开放下载。此次 MuMu 新版本修改了 adb 路径、模拟器程序名及安装路径。
在更新了 MuMu 5.0 后
若使用 MuMu 的默认 adb，须重新检测或手动修改 MAA 中的 ｢设置 - 连接设置 - ADB 路径｣
原路径：{安装目录}\shell\adb.exe
新路径：{安装目录}\nx_main\adb.exe

若开启自动启动模拟器，须重新设置 ｢设置 - 启动设置 - 模拟器路径｣。
原路径：{安装目录}\shell\MuMuPlayer.exe
新路径：{安装目录}\nx_device\12.0\shell\MuMuNxDevice.exe

## 免责声明

本软件开源、免费，仅供学习交流使用。若您遇到商家使用本软件进行代练并收费，可能是分发、设备或时间等费用，产生的费用、问题及后果与本项目无关。

在使用过程中，Maa_bbb 可能存在任何意想不到的 Bug，因 Maa_bbb 自身漏洞、文本理解有歧义、异常操作导致的账号问题等开发组不承担任何责任，请在确保在阅读完用户手册、自行尝试运行效果后谨慎使用！

只能说同类型项目没有被封案例，但是谁也无法保证百分之百不会被判定为外挂

游玩带有辅助检测的竞技类游戏（如CSGO，瓦罗兰特等）时，请尽量不要同时使用本助手

## 常用工具

1. 调试：[MaaDebugger](https://github.com/MaaXYZ/MaaDebugger) 进行调试json节点.
2. 截图、取色、取区域: [MFATools](https://github.com/SweetSmellFox/MFATools)
3. 战斗逻辑开发：[开发文档](https://github.com/miaojiuqing/Maa_bbb/blob/main/docs/zh_cn/%E6%88%98%E6%96%97%E9%80%BB%E8%BE%91%E7%BC%96%E5%86%99%E6%8C%87%E5%8D%97.md)

## 相关项目

1. [MaaFramework](https://github.com/MaaXYZ/MaaFramework)伟大无需多言，没有MaaFramework就没有MAA_bbb
2. [M9A](https://github.com/MAA1999/M9A)借鉴学习了不少思路，不愧是最佳实践.jpg
3. [HonkaiHelper](https://github.com/Aues6uen11Z/HonkaiHelper)我觉得这个项目很棒，学习了前置准备和一些日常任务完成方式
4. [MAA_Punish](https://github.com/overflow65537/MAA_Punish)同款自动战斗，原汁原味（因为是E佬写的战斗框架所以包原汁原味的）
5. [MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia/) — 社区 SweetSmellFox 编写的基于Avalonia的GUI，内置MaaFramework直接控制任务流程
6. [MFW-PyQt6](https://github.com/overflow65537/MFW-PyQt6) — 社区 overflow65537 编写的PyQt6 GUI，功能丰富，支持自定义任务流程
7. [AUTO-MAS](https://github.com/AUTO-MAS-Project/AUTO-MAS) — 多脚本统一管理平台，始于MAA但不止MAA，支持集中管理多个游戏自动化脚本

## 鸣谢

本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！

感谢以下开发者对本项目作出的贡献(还有开发群里的各位都很感谢):

<a href="https://github.com/miaojiuqing/MAA_bbb/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=miaojiuqing/MAA_bbb&max=1000" alt="Contributors to MAA_bbb"/>
</a>

## Star数量历史趋势

[![Star History Chart](https://api.star-history.com/svg?repos=miaojiuqing/Maa_bbb&type=date&legend=top-left)](https://www.star-history.com/#miaojiuqing/Maa_bbb&type=date&legend=top-left)

> 📈 星标增长趋势由 [star-history.com](https://star-history.com) 提供
