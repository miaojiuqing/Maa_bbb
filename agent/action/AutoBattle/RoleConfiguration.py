"""
崩坏3角色配置
"""

ROLE_CONFIG = {
    "真理之律者": {
        # 自动战斗的动作名
        "cls_name": "HerrscherOfTruth",
        "metadata": {
            "fire": 100,  # 角色输出的占比 fire|ice|lightning|physical
            "type": "mecha",  # 角色的属性 mech|psy|bio|qua|img|sd
            "weight": 2,  # 角色权重,数字越大,选人程序更容易选中
        },
        # 角色头像模板
        "template": [
            "自动战斗识别/真理之律者.png",
        ],
        # 角色攻击按键模板,用来在战斗内识别角色
        "attack_template": "自动战斗识别/真理之律者_atk.png",
    },
}
