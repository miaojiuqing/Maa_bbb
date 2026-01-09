from maa.agent.agent_server import AgentServer
from agent.custom.action.Count import Count
from agent.custom.action.OverridePipe import OverridePipe

from agent.custom.recongition.CheckResolution import CheckResolution


@AgentServer.custom_action("Count")
class Count_Cls(Count):
    pass


@AgentServer.custom_action("OverridePipe")
class OverridePipe_Cls(OverridePipe):
    pass


@AgentServer.custom_recognition("CheckResolution")
class CheckResolution_Cls(CheckResolution):
    pass
