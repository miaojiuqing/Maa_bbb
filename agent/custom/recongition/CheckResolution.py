from maa.context import Context
from maa.custom_recognition import CustomRecognition
from numpy import ndarray
import json
from ..utils.Logger import Logger


class CheckResolution(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult | None:
        logger = Logger("CheckResolution", context)
        param = json.loads(argv.custom_recognition_param)
        if not param:
            target_height = 720
            target_width = 1280
        else:
            target_height = param.get("height", 720)
            target_width = param.get("width", 1280)
        try:
            image: ndarray = argv.image
            height, width = image.shape[:2]
            logger.info(f"分辨率{width}x{height}")
            logger.info(f"目标分辨率{target_width}x{target_height}")
            if width != target_width or height != target_height:
                return CustomRecognition.AnalyzeResult(
                    box=[0, 0, 0, 0],
                    detail={
                        "status": "error",
                        "message": f"分辨率{width}x{height} 错误",
                    },
                )
            else:
                return None
        except Exception as e:
            print(f"Error in CheckResolution: {e}")
            return None
