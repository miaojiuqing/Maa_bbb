import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from agent.deploy.deploy import deploy


def main():
    from maa.agent.agent_server import AgentServer
    from maa.toolkit import Toolkit

    Toolkit.init_option("./")

    socket_id = sys.argv[-1]

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":

    # 在运行主程序之前进行部署检查
    if not deploy():
        print("部署检查失败，程序退出")
        sys.exit(1)

    from .CustomFile import *

    main()
