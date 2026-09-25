from maa.agent.agent_server import AgentServer
from agent.custom.action.Count import Count
from agent.custom.action.OverridePipe import OverridePipe
from agent.custom.action.IDFRole import RecognitionRole

from agent.custom.action.Notice import Notice

# 圣痕洗词缀 V2（智能版：下拉框选属性/武器类别 + 目标总攻击力）
from agent.custom.action.AffixRerollV2 import AffixRerollV2, AffixRerollV2ParamHolder

from agent.custom.action.Role.FieryWishingStar import FieryWishingStar
from agent.custom.action.Role.SpinaAstera import SpinaAstera
from agent.custom.action.Role.HerrscherOfTruth import HerrscherOfTruth
from agent.custom.action.Role.LoveElf import LoveElf
from agent.custom.action.Role.FengHuangOfVicissitude import FengHuangOfVicissitude
from agent.custom.action.Role.GeneralFight import GeneralFight  # 真理之律者
from agent.custom.action.Role.Mobius import Mobius  # 梅比乌斯


from agent.custom.recongition.CheckResolution import CheckResolution


@AgentServer.custom_action("Notice")
class Notice_Cls(Notice):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("GeneralFight")
# 真理之律者
class GeneralFight_Cls(GeneralFight):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("Mobius")
# 梅比乌斯
class Mobius_Cls(Mobius):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("IDFRole")
# IDF 角色识别
class IDFRole_Cls(RecognitionRole):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("Count")
class Count_Cls(Count):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("OverridePipe")
class OverridePipe_Cls(OverridePipe):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_recognition("CheckResolution")
class CheckResolution_Cls(CheckResolution):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("FieryWishingStar")
class FieryWishingStar_Cls(FieryWishingStar):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("SpinaAstera")
class SpinaAstera_Cls(SpinaAstera):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("HerrscherOfTruth")
class HerrscherOfTruth_Cls(HerrscherOfTruth):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("LoveElf")
class LoveElf_Cls(LoveElf):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("FengHuangOfVicissitude")
class FengHuangOfVicissitude_Cls(FengHuangOfVicissitude):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("AffixRerollV2")
# 圣痕洗词缀 V2（智能版）
class AffixRerollV2_Cls(AffixRerollV2):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("AffixRerollV2ParamHolder")
# 界面参数的载体节点（空动作）
class AffixRerollV2ParamHolder_Cls(AffixRerollV2ParamHolder):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")
