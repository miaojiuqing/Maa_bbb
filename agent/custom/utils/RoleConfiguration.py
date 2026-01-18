"""
崩坏3角色配置
"""

ROLE_CONFIG = {
    "真理之律者": {
        # 自动战斗的动作名
        "cls_name": "HerrscherOfTruth",
        "metadata": {
            "DMG": "ice",  # 角色输出类型 fire|ice|lightning|physical
            "type": "mecha",  # 角色的属性 mech|psy|bio|qua|img|sd
            "weight": 2,  # 角色权重,数字越大,选人程序更容易选中
        },
        # 角色头像模板
        "template": [
            "自动战斗识别/真理之律者.png",
        ],
        # 角色攻击按键模板,用来在战斗内识别角色
        "attack_template": "自动战斗索引/真理之律者.png",
    },
    "爱愿妖精": {
        # 自动战斗的动作名
        "cls_name": "LoveElf",
        "metadata": {
            "DMG": "ice",  # 角色输出类型 fire|ice|lightning|physical
            "type": "sd",  # 角色的属性 mech|psy|bio|qua|img|sd
            "weight": 2,  # 角色权重,数字越大,选人程序更容易选中
        },
        # 角色头像模板
        "template": [
            "自动战斗识别/爱愿妖精.png",
        ],
        # 角色攻击按键模板,用来在战斗内识别角色
        "attack_template": "自动战斗索引/爱愿妖精.png",
    },
    "崩落符": {
        # 自动战斗的动作名
        "cls_name": "FengHuangOfVicissitude",
        "metadata": {
            "DMG": "fire",  # 角色输出类型 fire|ice|lightning|physical
            "type": "bio",  # 角色的属性 mech|psy|bio|qua|img|sd
            "weight": 2,  # 角色权重,数字越大,选人程序更容易选中
        },
        # 角色头像模板
        "template": [
            "自动战斗识别/崩落符.png",
        ],
        # 角色攻击按键模板,用来在战斗内识别角色
        "attack_template": "自动战斗索引/崩落符.png",
    },
    "孑遗千星": {
        # 自动战斗的动作名
        "cls_name": "SpinaAstera",
        "metadata": {
            "DMG": "fire",  # 角色输出类型 fire|ice|lightning|physical
            "type": "mecha",  # 角色的属性 mech|psy|bio|qua|img|sd
            "weight": 2,  # 角色权重,数字越大,选人程序更容易选中
        },
        # 角色头像模板
        "template": [
            "自动战斗识别/孑遗千星.png",
        ],
        # 角色攻击按键模板,用来在战斗内识别角色
        "attack_template": "自动战斗索引/孑遗千星.png",
    },
    "炽愿吉星": {
        # 自动战斗的动作名
        "cls_name": "FieryWishingStar",
        "metadata": {
            "DMG": "fire",  # 角色输出类型 fire|ice|lightning|physical
            "type": "sd",  # 角色的属性 mech|psy|bio|qua|img|sd
            "weight": 2,  # 角色权重,数字越大,选人程序更容易选中
        },
        # 角色头像模板
        "template": [
            "自动战斗识别/炽愿吉星.png",
        ],
        # 角色攻击按键模板,用来在战斗内识别角色
        "attack_template": "自动战斗索引/炽愿吉星.png",
    },
}
