import sys
import os

print("info: 1111111")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.deploy.deploy import deploy

print(f"info: {os.getcwd()}")


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
        print("error: 部署检查失败，程序退出")
        sys.exit(1)

    from agent.CustomFile import *

    try:
        main()
    except Exception as e:
        print(f"error: 程序运行错误: {e}")
        sys.exit(1)
