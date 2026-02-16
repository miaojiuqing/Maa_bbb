from maa.agent.agent_server import AgentServer
from agent.custom.action.Count import Count
from agent.custom.action.OverridePipe import OverridePipe
from agent.custom.action.IDFRole import RecognitionRole

from agent.custom.action.Notice import Notice

from agent.custom.action.Role.FieryWishingStar import FieryWishingStar
from agent.custom.action.Role.SpinaAstera import SpinaAstera
from agent.custom.action.Role.HerrscherOfTruth import HerrscherOfTruth
from agent.custom.action.Role.LoveElf import LoveElf
from agent.custom.action.Role.FengHuangOfVicissitude import FengHuangOfVicissitude
from agent.custom.action.Role.GeneralFight import GeneralFight


from agent.custom.recongition.CheckResolution import CheckResolution


@AgentServer.custom_action("Notice")
class Notice_Cls(Notice):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("GeneralFight")
class GeneralFight_Cls(GeneralFight):
    def __init__(self):
        super().__init__()
        print(f"{self.__class__.__name__} 初始化")


@AgentServer.custom_action("IDFRole")
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
