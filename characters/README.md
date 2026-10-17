# 角色出招表

每个 JSON 文件描述一个角色的一个乐土流派。文件名可以自定义，但必须放在本目录并使用 `.json` 后缀。

最小结构如下：

```json
{
  "character": "角色名",
  "variant": "流派标识",
  "profile": {
    "requires_signet": "核心刻印名",
    "opening": ["support_1", "support_2"],
    "cycle": ["weapon"],
    "interval_ms": 120,
    "support_interval_s": 30
  },
  "touch_actions": {
    "weapon": [1045, 512]
  }
}
```

`cycle` 和 `opening` 使用 `CharacterCombat` 支持的动作名。常用动作包括 `attack`、`weapon`、`support_1`、`support_2`、`elysian_support`、`ultimate`、`star_ring`、`dodge`、`movement` 和 `branch`。新增配置后，需要在 `tasks/周常/往世乐土.json` 的角色下拉框中注册对应的 `character` 和 `variant`。

可选字段 `hold_attack`（布尔，默认 `false`）：为 `true` 时战斗中**全程按住普攻**——开始战斗时按下、战斗结束/停止/异常时自动松开；按住期间不执行 `attack` 点按，也不触发 `branch`（两者共用普攻按钮，互斥）。按下与松开分别使用资源包节点 `按下攻击_action` / `松开攻击_action`，安卓端为触摸、桌面端为按键。
