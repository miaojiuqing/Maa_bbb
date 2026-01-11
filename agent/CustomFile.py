from maa.agent.agent_server import AgentServer
from agent.custom.action.Count import Count
from agent.custom.action.OverridePipe import OverridePipe
from agent.custom.action.IDFRole import RecognitionRole


from agent.custom.action.Role.FieryWishingStar import FieryWishingStar
from agent.custom.action.Role.SpinaAstera import SpinaAstera
from agent.custom.action.Role.HerrscherOfTruth import HerrscherOfTruth
from agent.custom.action.Role.LoveElf import LoveElf
from agent.custom.action.Role.FengHuangOfVicissitude import FengHuangOfVicissitude
from agent.custom.action.Role.GeneralFight import GeneralFight


from agent.custom.recongition.CheckResolution import CheckResolution


@AgentServer.custom_action("GeneralFight")
class GeneralFight_Cls(GeneralFight):
    pass


@AgentServer.custom_action("IDFRole")
class IDFRole_Cls(RecognitionRole):
    pass


@AgentServer.custom_action("Count")
class Count_Cls(Count):
    pass


@AgentServer.custom_action("OverridePipe")
class OverridePipe_Cls(OverridePipe):
    pass


@AgentServer.custom_recognition("CheckResolution")
class CheckResolution_Cls(CheckResolution):
    pass


@AgentServer.custom_action("FieryWishingStar")
class FieryWishingStar_Cls(FieryWishingStar):
    pass


@AgentServer.custom_action("SpinaAstera")
class SpinaAstera_Cls(SpinaAstera):
    pass


@AgentServer.custom_action("HerrscherOfTruth")
class HerrscherOfTruth_Cls(HerrscherOfTruth):
    pass


@AgentServer.custom_action("LoveElf")
class LoveElf_Cls(LoveElf):
    pass


@AgentServer.custom_action("FengHuangOfVicissitude")
class FengHuangOfVicissitude_Cls(FengHuangOfVicissitude):
    pass
