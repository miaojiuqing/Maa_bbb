# YOLO11n ONNX 模型使用说明

## 模型信息
- **模型来源**：由 YOLO11n 模型转换而来
- **文件路径**：`d:\Maa_bbb\onnx\best.onnx`
- **转换框架**：PyTorch 2.7.1

## 输入格式

### 输入张量
- **名称**：`images`
- **形状**：`[1, 3, 384, 640]`
  - 维度解释：`[batch_size, channels, height, width]`
  - `batch_size`：固定为 1
  - `channels`：3（RGB 通道）
  - `height`：384
  - `width`：640
- **数据类型**：float32
- **预处理要求**：
  1. 图像 resize 到 640x384 像素
  2. 归一化：将像素值除以 255.0 缩放到 [0, 1] 范围
  3. 通道顺序：RGB（不是 BGR）
  4. 维度顺序：NCHW（不是 NHWC）

## 输出格式

### 输出张量
- **名称**：`output0`
- **形状**：`[1, 28, 5040]`
  - 维度解释：`[batch_size, num_attributes, num_boxes]`
  - `batch_size`：固定为 1
  - `num_attributes`：28（4 个坐标 + 1 个置信度 + 23 个类别概率）
  - `num_boxes`：5040（预测框数量）
- **数据类型**：float32

### 输出解析
对于每个预测框（共 5040 个），输出包含 28 个属性：
1. **坐标信息**（前 4 个值）：
   - `output[0, 0, i]`：预测框中心点 x 坐标（归一化到 0-1）
   - `output[0, 1, i]`：预测框中心点 y 坐标（归一化到 0-1）
   - `output[0, 2, i]`：预测框宽度（归一化到 0-1）
   - `output[0, 3, i]`：预测框高度（归一化到 0-1）
2. **置信度**（第 5 个值）：
   - `output[0, 4, i]`：预测框的置信度分数
3. **类别概率**（后 23 个值）：
   - `output[0, 5:28, i]`：各个类别的预测概率

## 重要注意事项
- **不自带 NMS**：模型输出未经过非极大值抑制（NMS）处理，需要在使用时自行实现
- **坐标归一化**：输出坐标是归一化值，需要根据原始图像尺寸进行反归一化
- **置信度阈值**：建议设置适当的置信度阈值来过滤低置信度的预测

## 使用示例

### Python 示例代码
```python
import onnxruntime as ort
import numpy as np
from PIL import Image

# 加载模型
session = ort.InferenceSession('d:\Maa_bbb\onnx\best.onnx')
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

# 加载和预处理图像
image = Image.open('test.jpg').resize((640, 384))
image_array = np.array(image).astype(np.float32) / 255.0
image_array = image_array.transpose(2, 0, 1)  # HWC -> CHW
image_array = np.expand_dims(image_array, axis=0)  # 添加 batch 维度

# 推理
output = session.run([output_name], {input_name: image_array})
output = output[0]

# 处理输出（需要自行实现 NMS）
# 1. 过滤低置信度预测
# 2. 应用 NMS
# 3. 反归一化坐标到原始图像尺寸
# 4. 获取最终检测结果
```

### 输出后处理步骤
1. **过滤低置信度预测**：设置置信度阈值（如 0.5），过滤掉置信度低于阈值的预测框
2. **应用 NMS**：对剩余预测框应用非极大值抑制，去除重叠的框
3. **坐标转换**：将归一化坐标转换为原始图像的像素坐标
4. **类别分配**：根据类别概率确定每个预测框的类别

## 模型性能
- **输入分辨率**：640x384
- **预测框数量**：5040
- **类别数量**：23
- **推理速度**：取决于硬件设备，在 GPU 上可达到实时性能

## 常见问题
1. **图像预处理错误**：确保输入图像按照要求进行 resize 和归一化
2. **坐标解析错误**：注意输出坐标是归一化值，需要根据原始图像尺寸进行转换
3. **检测效果不佳**：尝试调整置信度阈值和 NMS 参数

## 版本信息
- YOLO11n 原始模型
- ONNX 转换版本：PyTorch 2.7.1