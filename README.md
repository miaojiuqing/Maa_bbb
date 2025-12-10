<!-- markdownlint-disable MD033 MD041 -->

<p align="center">
  <img alt="LOGO" src="logo.ico" width="256" height="256" />
</p>

<div align="center">

## Maa_bbb

(识宝小助手)

基于MAA框架制作的崩坏三小助手。图像技术 + 模拟控制，解放双手！由 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 强力驱动！

[点击申请加入小助手交流群](<https://qm.qq.com/q/XrFQKgGvaI>)

[国内在线文档]还没写
更多功能敬请期待（提issus）
正处于开发阶段，自动战斗极速画饼中）

</div>
<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white">
  <img alt="license" src="https://img.shields.io/github/license/miaojiuqing/Maa_bbb">
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows-blueviolet">
  <img alt="commit" src="https://img.shields.io/github/commit-activity/m/miaojiuqing/Maa_bbb">
   <a href="https://mirrorchyan.com/zh/projects?rid=Maa_bbb" target="_blank"><img alt="mirrorc" src="https://img.shields.io/badge/Mirror%E9%85%B1-%239af3f6?logo=countingworkspro&logoColor=4f46e5"></a>
</p>

  <br/>
</p>
---

## 简介

**Maa_bbb** 是由miaojiuqing（淼九清）开发的游戏自动化工具，旨在帮助玩家完成每日任务，和以后会添加的一些小活动。  
**注意：** 本项目推荐使用mumu模拟器(好用)、雷电模拟器，其他模拟器没测过,当然PC端也同步适配，请自己设置为16:9分辨率

[视频链接](<https://www.bilibili.com/video/BV1Ld42z1ERu/?vd_source=49383a2ec38e99b49eb1e3f17c256fb9#reply279196116704>)

[点击链接加入群聊](<https://qm.qq.com/q/XrFQKgGvaI>)

---
<details>
<summary>PC端使用须知</summary>

## PC端使用须知

  目前已经可以实现后台点击运行，请舰长在软件中的 设置——连接设置——鼠标输入/键盘输入中选择PostMessageWithCursorPos或者SendMessageWithCursorPos即可，请注意:自动战斗(和所有涉及键码输入的)无法使用后台运行功能

  需提前在 [b]:设置 -辅助中，关闭显示菜单提示

 ![操作图指引](<https://s21.ax1x.com/2025/10/16/pVqBJde.md.png>)

  错误示例

 ![错误示例](<https://s21.ax1x.com/2025/10/16/pVqBYIH.md.png>)

  正确首页

 ![正确页面](<https://s21.ax1x.com/2025/10/16/pVqBNid.md.png>)
</details>

<details>
<summary>嘿蓬油，你这脚本怎么不会动的</summary>

## 请检查自己的分辨率

- 请检查设置-画质-分辨率

  检查其中的分辨率是否为16:9，不会算的话截屏问AI“请问图中所展示的分辨率哪些是16:9”

- 请检查您启动时是否是以管理员方式启动

- 请通过截图测试查看当前截图是否正常，若非正常请自行更换截图方式
  
</details>

## 主要功能

### 启动

- [x] 启动游戏并打开菜单

### 日常

- [x] 材料远征
- [X] 家园金币领取
- [X] 家园打工
- [X] 家园远征
- [X] 舰团每日委托
- [X] 领取日常任务奖励
- [X] 领取凭证任务奖励
- [X] 领取邮件奖励
- [X] 舰团保税物品申请(我真是闲得慌做这玩意)

### 周常

- [X] 自动超弦空间(老登苦痛一以下无压力)
  - [X] 自动切换制定编队
  - [X] 自选战斗逻辑
  - [x] 是否只打前三层
- [X] 每周答题-减负
- [X] 每周分享
- [X] 冒险委托-减负(话说这算周常还是日常)
  - [X] 轮回之樱
  - [X] 后崩坏书1
  - [x] 后崩坏书2
  - [X] 天命总部
- [X] 记忆战场战场-减负
- [X] 万象虚境-减负
  - [X] 层数选择
  - [X] 副本选择
  - [x] 是否消耗时序通行证
  - [X] 挑战次数选择
- [X] 模拟作战室-减负

### 乐土

- [ ] 自动乐土（目前仅导航至乐土箱庭）

- [X] 克莱茵打灰（刷装甲等级/乐土币/萌新刷命定歧路）
  - [X] 减负模式-无限刷
  - [ ] 浅层序列刷
  - [X] 首层复刷
  - [X] 无限刷取模式

### 商店

- [x] 每日商店选购
  - [x] 后勤终端
    - [x] 只购买星石为货币的商品
    - [x] 只购买金币为货币的商品
    - [x] 购买所有货币为星石和金币的商品
  - [x] 每日金币商店普通晶体核心购买
- [X] 每周商店选购
  - [X] 1星石的虚境挑战书
  - [x] 吼姆秘藏
- [X] 每周乐土商店(自选购买商品)
  - [X] 吼吼休假卷
  - [x] 相转移镜面
  - [X] 聚能·空间透镜
  - [x] 虚境挑战书
- [ ] 每月商店选购
- [ ] 每版本商店选购-----------我感觉这个好像没必要做啊，每个版本相隔的天数都不一样

### 活动

- [X] 活动日常(太难的不做，有PVP元素/会影响其他玩家的不做)
  - [X] 当期为欢咻电玩屋

### 额外功能

- [X] 自动战斗
  - [X] 乐土版
    - [X] 通用战斗逻辑(开环/开人偶流)
    - [X] 通用战斗逻辑(禁环/禁人偶流)
    - [X] 薇塔(开环流)
    - [ ] 新春虫(开环流)
    - [X] 崩落符(普攻流)-PC用，模拟器不建议用，A太慢了，严格来说自动战斗这个功能目前是不推荐模拟器用户去使用的
    - [X] 嗨♪爱愿妖精(开环流)
  - [ ] 超弦空间/量子流行版
    - [ ] 虚三家
- [X] 自动过剧情
  - [X] 纯点击跳过（就是看到跳过就会点击，会自己点掉今日不再显示的提示可能会错过CG收集）
  - [x] 无视跳过正常过剧情-手动选择选项（正常过剧情，遇到对话选项会停）
  - [x] 无视跳过正常过剧情-自动选择选项（正常过剧情，遇到对话选项会自己选择最上面的）
  - [x] 古早剧情的点击跳过（很老的那种，两个悬浮窗在那）

### 关于UI使用选择

## MFAAvalonia

- 默认为MFA阿瓦隆，可以满足大部分要求，打包自动发版

## MFW-PyQt6

- 若希望某些任务可以一周执行一次的话可以使用此UI，具体任务流程需自行配置
- 下载[releases](https://github.com/overflow65537/MFW-PyQt6/releases)包

## MFW-mq

- 好想自己写一个UI()

### 关于使用模拟器还是win32

#### ADB(模拟器)

- 软件启动后左上角资源选择选择“模拟器”，然后右边检查窗口是否为“下载了崩坏三的模拟器”，模拟器分辨率自行设置为16:9，可以挂后台！

#### win32(电脑客户端)

- 软件管理员启动后左上角资源选择选择“桌面端”，然后右边检查窗口是否为“崩坏3”，游戏内窗口自行设置为16:9(你开全屏分辨率是16:9就能全屏用，不能就乖乖窗口化)，触控与截屏模式默认即可，没法挂后台！以后会适配后台(大概吧)

### 常见问题

提问前请检查

模拟器

  模拟器的分辨率是否为16:9

  任务名中带“减负”字样的任务你是否解锁减负功能

PC端

  左上角的资源选择是否为“桌面端”

  游戏分辨率是否为16:9

  游戏辅助菜单是否已关闭(关闭方法在上面)

  游戏操控方式是否为键鼠(计划后续添加纯键盘自愿选择)

  软件右上角的窗口选择是否为崩坏3

快问快答

Q:我软件启动之后显示“资源加载失败”怎么办

A1:打开安装目录，删除除了config之外的文件夹，然后下载最新版拖入安装目录，之后再次启动即可

#######

A2:作者搞错了，等更新，一般半小时之内解决
  
Q:我是XXX渠道服的，我在软件资源列表未寻找到我的渠道服的资源

A:包名给我，手机抓取包名方法为：启动你要抓取包名的崩坏3后，切换后台，设置-应用-找到你刚刚启动的要抓取包名的崩坏3，点进去会显示包名,复制给我就好

  如果是模拟器的话，直接进群发送APK文件给我我来抓就好

#######

Q:我任务奖励领取功能一直不点是为啥

A:你黑边没关，滑到最上面看一下如何关闭

#######

Q:怎么导出日志

A:软件内点击|→即可导出日志，若该bug可以稳定复现的话最好导出前删除debug文件夹之后再触发一次bug之后再导出

### 作者告诫

- 本助手完全免费，没有任何收费的地方！！！！！！！！！！！！！！！！！！！！如果你是买来的请举报并拉黑商家顺便告诉我谁卖的
- 请注意!!!**以上任务的运行基本都基于菜单界面才能开始运行**

1. 点击链接下载最新[Release](https://github.com/miaojiuqing/Maa_bbb/releases)包

2.安装运行环境
-Windows

·对于Windows需要在运行前安装运行库。

-需要 VCRedist x64 (cli与gui都需要) 和 .NET 10 (仅使用gui时需要)。 点击 vc_redist.x64 下载安装 VCRedist x64，点击 dotnet-sdk-8.0.5-win-x64.exe 下载安装.NET 10。 也可以开始安装目录内，运行DependencySetup_依赖库安装_win.bat以进行安装。
3. 解压后双击`MFAAvalonia.exe`即可运行

可以通过创建快捷方式之后，右键该快捷方式,点击属性自行更改图标

### Windows

- 对于绝大部分用户，请下载 Maa_bbb-win-x86_64.zip
- 若确定自己的电脑是 arm 架构，请下载 Maa_bbb-win-x86_64.zip
- 请注意！Windows 的电脑几乎全都是 x86_64 的，可能占 99.999%，除非你非常确定自己是 arm，否则别下这个！_
- 解压后运行 MFAAvalonia.exe（图形化界面，推荐使用，老版本UI为MFAWPF.exe）或 MaaPiCli.exe（命令行）即可

### macOS

没接触过

### Linux

都用Linux了一定是大佬，大佬会自己改的（确信

## 图形化界面

- <span style="font-size:25px;">[MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia/)</span>  
- 由社区大佬[SweetSmellFox](https://github.com/SweetSmellFox)编写的基于Avalonia的GUI,通过内置的MAAframework来直接控制任务流程  
- 打开本程序和模拟器后，先在右上方选择要控制的模拟器  
- 勾选想要执行的任务后**开始任务**，任务会顺序执行，所有任务都需要游戏为开启状态  
- 点击部分任务右方的设置，可以配置任务属性

## 注意事项

- 提示“应用程序错误”，一般是缺少运行库，请尝试安装 [vc_redist](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- 添加 `-d` 参数可跳过交互直接运行任务，如 `./MaaPiCli.exe -d`（这段话啥意思不是很清楚我这个网页用别人的改的
- MAA framework 2.0 版本已支持 mumu 后台保活，会在 run task 时获取 mumu 最前台的 tab
- 反馈问题请附上日志文件 `debug/maa.log`以及问题界面的截图，谢谢！

## 关于新版mumu模拟器如何连接

近期 MuMu 模拟器 5.0 正在进行内测，并预计将于 6 月 20 日起陆续开放下载。此次 MuMu 新版本修改了 adb路径、模拟器程序名及安装路径。
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

## 鸣谢

本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！

感谢以下开发者对本项目作出的贡献(还有开发群里的各位都很感谢):

<a href="https://github.com/miaojiuqing/MAA_bbb/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=miaojiuqing/MAA_bbb&max=1000" alt="Contributors to MAA_bbb"/>
</a>
