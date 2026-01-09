from maa.context import Context
from maa.custom_action import CustomAction
import json
from ..utils.Logger import Logger


class OverridePipe(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        """
        覆盖pipeline配置
        custom_action_param:
            {
                "type": "resource",
                "override_pipeline": {
                    "node1": {
                        "next": ["node2"]
                    }
                }
            }
            type: 类型  resource: 资源  tasker: 任务器
            override_pipeline: 覆盖的内容
        """

        logger = Logger("Override_Pipe", context)
        param: dict = json.loads(argv.custom_action_param)
        logger.info(f"Override_Pipe: {param}")
        if param.get("type") == "resource":
            context.tasker.resource.override_pipeline(
                param.get("override_pipeline", {})
            )

        elif param.get("type") == "tasker":
            context.override_pipeline(param.get("override_pipeline", {}))
        else:
            context.override_pipeline(param.get("override_pipeline", {}))
            logger.error(f"Override_Pipe: 类型错误")

        logger.destroy()
        return CustomAction.RunResult(success=True)
