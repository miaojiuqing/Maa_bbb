import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.deploy.deploy import deploy, get_main_py_path


def main():

    from maa.agent.agent_server import AgentServer
    from maa.toolkit import Toolkit

    Toolkit.init_option("./")

    socket_id = sys.argv[-1]
    print(f"socket_id: {socket_id}")

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    # 在运行主程序之前进行部署检查
    git_path = get_main_py_path().parent.parent / ".git"
    if git_path.exists():
        print("测试模式,. 不进行部署检查")
        if len(sys.argv) == 1:
            sys.argv.append("MAA_AGENT_SOCKET")
    elif not deploy():
        print("error: 部署检查失败，程序退出")
        sys.exit(1)

    from agent.CustomFile import *

    try:
        main()
    except Exception as e:
        print(f"error: 程序运行错误: {e}")
        sys.exit(1)
