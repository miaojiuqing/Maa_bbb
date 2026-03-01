# YOLO ONNX 模型使用说明

## 1. 模型简介

**模型名称**: best.onnx
**模型类型**: YOLO 目标检测模型 (ONNX 格式)
**模型架构**: YOLO10n
**输入尺寸**: 640×384
**输出格式**: 每个检测框包含 [x1, y1, x2, y2, confidence, class_id]

## 2. 可识别的类别

该模型可以识别以下 24 个类别：

| 类别ID | 类别名称 | 中文解释 |
|--------|----------|----------|
| 0 | elysia_star | 爱愿妖精 |
| 1 | aomie | 鏖灭 |
| 2 | zhenwo | 真我 |
| 3 | kongmeng | 空梦 |
| 4 | shanbiyvjing | 闪避预警 |  #（不可用）
| 5 | xuanze_R | 选择_R |  #（不可用）
| 6 | guaiwu_xueliang_UI | 怪物血量_UI |
| 7 | xuanze_r | 选择_r |  #（不可用）
| 8 | keyin | 刻印门 |
| 9 | keyin_open | 打开的刻印门 |
| 10 | shangdian | 商店门 |
| 11 | jielv | 戒律 |
| 12 | luoxuan | 螺旋 |
| 13 | shangdian_open | 开着的商店 |
| 14 | tianhui | 天慧 |
| 15 | fanxing | 繁星 |
| 16 | lock_on | 锁定 |  #（不可用）
| 17 | wuxian | 无限 |
| 18 | chana | 刹那 |
| 19 | huangjin | 黄金 |
| 20 | jiushi | 救世 |
| 21 | xvguang | 旭光 |
| 22 | fusheng | 浮生 |
| 23 | BOSS | BOSS门 |

## 3. 环境要求

### 3.1 Python 环境依赖

#### 3.1.1 必需依赖

- **Python 3.8+**
- **ONNX Runtime**: `pip install onnxruntime` (官方推荐的 ONNX 推理引擎)
- **OpenCV**: `pip install opencv-python` (用于图像处理)
- **NumPy**: `pip install numpy` (用于数据处理)

#### 3.1.2 可选依赖

- **Ultralytics**: `pip install ultralytics` (提供更简单的模型加载和使用方式)
- **ONNX**: `pip install onnx` (用于模型验证和检查)

### 3.2 C++ 环境依赖

#### 3.2.1 必需依赖

- **ONNX Runtime C++ API**: 从 [官方网站](https://onnxruntime.ai/) 下载对应平台的库（建议版本 1.15+）
- **OpenCV**: 从 [OpenCV 官网](https://opencv.org/releases/) 下载并安装（建议版本 4.5+）
- **C++11 或更高版本的编译器**

#### 3.2.2 构建工具

- **CMake 3.13+**
- **Visual Studio** (Windows) 或 **GCC** (Linux/Mac)

### 3.3 依赖版本建议

为了确保兼容性，建议使用以下版本或更高版本：

| 依赖 | 建议版本 |
|------|----------|
| Python | 3.8+ |
| ONNX Runtime | 1.15+ |
| OpenCV-Python | 4.5+ |
| NumPy | 1.20+ |
| Ultralytics (可选) | 8.0+ |

**版本检查命令**：

```bash
# 检查 Python 包版本
python -c "import onnxruntime; print(f'ONNX Runtime: {onnxruntime.__version__}')"
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
# 如果安装了 Ultralytics
python -c "try: import ultralytics; print(f'Ultralytics: {ultralytics.__version__}'); except: print('Ultralytics not installed')"
```

## 4. 使用方法

### 4.1 方法一：使用 Ultralytics YOLO 库

```python
from ultralytics import YOLO
import cv2

# 加载 ONNX 模型
model = YOLO('best.onnx')

# 预测图片
results = model('test.jpg', conf=0.25)

# 处理结果
result = results[0]
for box in result.boxes:
    # 获取边界框坐标
    coords = box.xyxy[0].tolist()
    # 获取置信度
    confidence = box.conf[0].item()
    # 获取类别ID
    class_id = int(box.cls[0].item())
    # 获取类别名称
    class_name = result.names[class_id]
    
    print(f"类别: {class_name}, 置信度: {confidence:.4f}, 坐标: {coords}")

# 保存结果图片
result.save(filename='result.jpg')
```

### 4.2 方法二：使用 ONNX Runtime 直接加载

```python
import onnxruntime as ort
import cv2
import numpy as np

# 类别名称映射
class_names = [
    "elysia_star", "aomie", "zhenwo", "kongmeng", "shanbiyvjing", "xuanze_R", 
    "guaiwu_xueliang_UI", "xuanze_r", "keyin", "keyin_open", "shangdian", 
    "jielv", "luoxuan", "shangdian_open", "tianhui", "fanxing", "lock_on", 
    "wuxian", "chana", "huangjin", "jiushi", "xvguang", "fusheng", "BOSS"
]

# 中文解释映射
class_names_cn = [
    "爱愿妖精", "鏖灭", "真我", "空梦", "闪避预警", "选择_R", "怪物血量_UI", "选择_r",
    "刻印门", "打开的刻印门", "商店门", "戒律", "螺旋", "开着的商店", "天慧",
    "繁星", "锁定", "无限", "刹那", "黄金", "救世", "旭光", "浮生", "BOSS门"
]

def preprocess_image(image_path, input_size=(640, 384)):
    """预处理图片 (根据模型要求: 640x384)"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图片: {image_path}")
    
    # 记录原始尺寸
    orig_h, orig_w = img.shape[:2]
    
    # 调整尺寸并转换为RGB
    img_resized = cv2.resize(img, input_size)
    img_resized = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    
    # 归一化和转置 (HWC -> CHW)
    img_tensor = img_resized.transpose((2, 0, 1)).astype(np.float32) / 255.0
    img_tensor = np.expand_dims(img_tensor, axis=0)  # 添加batch维度
    
    return img_tensor, orig_w, orig_h

def postprocess_output(output, orig_width, orig_height, pre_width=640, pre_height=384, conf_threshold=0.25):
    """
    后处理输出
    
    参数:
        output: ONNX模型输出 (格式: [batch_size, num_boxes, 6])
                每个检测框: [x1, y1, x2, y2, confidence, class_id]
        orig_width, orig_height: 原始图像尺寸
        pre_width, pre_height: 预处理后图像尺寸
        conf_threshold: 置信度阈值
    """
    predictions = []
    
    # 模型输出格式: (batch_size, num_boxes, 6) → [x1, y1, x2, y2, confidence, class_id]
    if len(output) == 0:
        return predictions
    
    # 取第一个batch的输出
    boxes = output[0]
    
    # 过滤低置信度的框
    if len(boxes) > 0:
        boxes = boxes[boxes[:, 4] > conf_threshold]
        
        # 按置信度排序
        if len(boxes) > 0:
            boxes = boxes[boxes[:, 4].argsort()[::-1]]
            
            # 计算缩放比例
            scale_x = orig_width / pre_width
            scale_y = orig_height / pre_height
            
            for box in boxes:
                class_id = int(box[5])
                confidence = float(box[4])
                
                # 确保class_id在有效范围内
                if 0 <= class_id < len(class_names):
                    # 调整边界框坐标到原始图像尺寸
                    x1 = box[0] * scale_x
                    y1 = box[1] * scale_y
                    x2 = box[2] * scale_x
                    y2 = box[3] * scale_y
                    
                    predictions.append({
                        "class_id": class_id,
                        "class_name": class_names[class_id],
                        "class_name_cn": class_names_cn[class_id],
                        "confidence": confidence,
                        "bbox": [float(x1), float(y1), float(x2), float(y2)]
                    })
    
    return predictions

# 加载模型
session = ort.InferenceSession('best.onnx', providers=['CPUExecutionProvider'])

# 获取输入名称
input_name = session.get_inputs()[0].name

# 预处理图片
img_tensor, orig_width, orig_height = preprocess_image('test.jpg', input_size=(640, 384))

# 推理
outputs = session.run(None, {input_name: img_tensor})

# 后处理
predictions = postprocess_output(outputs, orig_width, orig_height)

# 显示结果
if predictions:
    print(f"检测到 {len(predictions)} 个目标:")
    for i, pred in enumerate(predictions):
        print(f"\n目标 {i+1}:")
        print(f"  类别ID: {pred['class_id']}")
        print(f"  类别名称: {pred['class_name']}")
        print(f"  中文解释: {pred['class_name_cn']}")
        print(f"  置信度: {pred['confidence']:.4f}")
        bbox = pred['bbox']
        print(f"  边界框坐标: [{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}]")
        print(f"    - 左上角: ({bbox[0]:.2f}, {bbox[1]:.2f})")
        print(f"    - 右下角: ({bbox[2]:.2f}, {bbox[3]:.2f})")
else:
    print("未检测到任何目标")
```
### 4.3 方法四：使用 C++ 语言

#### 4.3.1 C++ 示例代码

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>
#include <opencv2/opencv.hpp>
#include <onnxruntime_cxx_api.h>

// 类别名称映射
std::vector<std::string> class_names = {
    "爱愿妖精", "鏖灭", "真我", "空梦", "闪避预警", "选择_R", "怪物血量_UI", "选择_r",
    "刻印门", "打开的刻印门", "商店门", "戒律", "螺旋", "开着的商店", "天慧",
    "繁星", "锁定", "无限", "刹那", "黄金", "救世", "旭光", "浮生", "BOSS门"
};

// 预处理图片
std::vector<float> preprocess_image(const cv::Mat& image, int input_width, int input_height) {
    cv::Mat resized, normalized;
    cv::resize(image, resized, cv::Size(input_width, input_height));
    resized.convertTo(normalized, CV_32F, 1.0 / 255.0);
    
    // HWC to CHW
    std::vector<float> input_data;
    for (int c = 0; c < 3; c++) {
        for (int h = 0; h < input_height; h++) {
            for (int w = 0; w < input_width; w++) {
                input_data.push_back(normalized.at<cv::Vec3f>(h, w)[c]);
            }
        }
    }
    return input_data;
}

// 后处理输出 - 针对 YOLOv8/v10 ONNX 格式
std::vector<std::map<std::string, float>> postprocess_output(
    const float* output_data,
    const std::vector<int64_t>& output_shape,
    int image_width, 
    int image_height, 
    int input_width, 
    int input_height, 
    float conf_threshold = 0.25f) {
    
    std::vector<std::map<std::string, float>> predictions;
    
    // 模型输出格式: [batch_size, num_boxes, 6] → [x1, y1, x2, y2, confidence, class_id]
    if (output_shape.size() != 3) {
        std::cerr << "错误: 输出维度应为3，实际为 " << output_shape.size() << std::endl;
        return predictions;
    }
    
    int batch_size = output_shape[0];
    int num_boxes = output_shape[1];
    int box_dim = output_shape[2];  // 应为6
    
    if (box_dim != 6) {
        std::cerr << "警告: 每个框的维度应为6，实际为 " << box_dim << std::endl;
    }
    
    // 计算缩放比例
    float scale_x = static_cast<float>(image_width) / input_width;
    float scale_y = static_cast<float>(image_height) / input_height;
    
    // 只处理第一个batch
    for (int i = 0; i < num_boxes; i++) {
        int offset = i * box_dim;
        
        // 读取框数据
        float x1 = output_data[offset];
        float y1 = output_data[offset + 1];
        float x2 = output_data[offset + 2];
        float y2 = output_data[offset + 3];
        float conf = output_data[offset + 4];
        int class_id = static_cast<int>(output_data[offset + 5]);
        
        // 过滤低置信度的框
        if (conf > conf_threshold) {
            // 调整到原始图像尺寸
            x1 *= scale_x;
            y1 *= scale_y;
            x2 *= scale_x;
            y2 *= scale_y;
            
            // 确保坐标在图像范围内
            x1 = std::max(0.0f, std::min(x1, static_cast<float>(image_width)));
            y1 = std::max(0.0f, std::min(y1, static_cast<float>(image_height)));
            x2 = std::max(0.0f, std::min(x2, static_cast<float>(image_width)));
            y2 = std::max(0.0f, std::min(y2, static_cast<float>(image_height)));
            
            // 确保边界框有效
            if (x2 > x1 && y2 > y1) {
                std::map<std::string, float> pred;
                pred["x1"] = x1;
                pred["y1"] = y1;
                pred["x2"] = x2;
                pred["y2"] = y2;
                pred["conf"] = conf;
                pred["class_id"] = static_cast<float>(class_id);
                predictions.push_back(pred);
            }
        }
    }
    
    return predictions;
}

int main() {
    try {
        // 初始化 ONNX Runtime
        Ort::Env env(OrtLoggingLevel::ORT_LOGGING_LEVEL_WARNING, "YOLOInference");
        Ort::SessionOptions session_options;
        session_options.SetIntraOpNumThreads(1);
        
        // 加载模型
        std::string model_path = "best.onnx";
        Ort::Session session(env, model_path.c_str(), session_options);
        
        // 获取输入信息
        Ort::AllocatorWithDefaultOptions allocator;
        auto input_info = session.GetInputTypeInfo(0);
        auto input_shape = input_info.GetTensorTypeAndShapeInfo().GetShape();
        int input_width = input_shape[3];
        int input_height = input_shape[2];
        
        // 读取图片
        cv::Mat image = cv::imread("test.jpg");
        if (image.empty()) {
            std::cerr << "Failed to read image" << std::endl;
            return 1;
        }
        
        int image_width = image.cols;
        int image_height = image.rows;
        
        // 预处理
        std::vector<float> input_data = preprocess_image(image, input_width, input_height);
        
        // 创建输入张量（避免变量名冲突）
        std::vector<int64_t> input_tensor_shape = {1, 3, input_height, input_width};
        Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
            allocator, input_data.data(), input_data.size(), 
            input_tensor_shape.data(), input_tensor_shape.size());
        
        // 设置输入名称
        const char* input_names[] = {"images"};
        
        // 获取输出名称（正确管理内存）
        size_t num_outputs = session.GetOutputCount();
        std::vector<std::string> output_name_strs(num_outputs);
        std::vector<const char*> output_names(num_outputs);
        for (size_t i = 0; i < num_outputs; i++) {
            char* output_name = session.GetOutputName(i, allocator);
            output_name_strs[i] = output_name;
            allocator.Free(output_name);
        }
        for (size_t i = 0; i < num_outputs; i++) {
            output_names[i] = output_name_strs[i].c_str();
        }
        
        // 推理
        auto output_tensors = session.Run(
            Ort::RunOptions{nullptr}, input_names, &input_tensor, 1, 
            output_names.data(), num_outputs);
        
        // 处理输出
        Ort::Value& output_tensor = output_tensors[0];
        float* output_data = output_tensor.GetTensorMutableData<float>();
        
        // 获取输出形状
        auto output_shape_info = output_tensor.GetTensorTypeAndShapeInfo();
        std::vector<int64_t> output_shape = output_shape_info.GetShape();
        size_t output_size = output_shape_info.GetElementCount();
        
        // 后处理
        float conf_threshold = 0.25f;
        auto predictions = postprocess_output(
            output_data, output_shape, image_width, image_height, 
            input_width, input_height, conf_threshold);
        
        // 绘制结果
        for (const auto& pred : predictions) {
            int class_id = static_cast<int>(pred.at("class_id"));
            float conf = pred.at("conf");
            float x1 = pred.at("x1");
            float y1 = pred.at("y1");
            float x2 = pred.at("x2");
            float y2 = pred.at("y2");
            
            std::string label = class_names[class_id] + " " + std::to_string(conf).substr(0, 5);
            cv::rectangle(image, cv::Point(x1, y1), cv::Point(x2, y2), cv::Scalar(0, 255, 0), 2);
            cv::putText(image, label, cv::Point(x1, y1 - 10), cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(0, 255, 0), 1);
            
            std::cout << "类别: " << class_names[class_id] << ", 置信度: " << conf 
                      << ", 坐标: [" << x1 << ", " << y1 << ", " << x2 << ", " << y2 << "]" << std::endl;
        }
        
        // 保存结果
        cv::imwrite("result.jpg", image);
        std::cout << "结果已保存到 result.jpg" << std::endl;
        
    } catch (const Ort::Exception& e) {
        std::cerr << "ONNX Runtime error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
```

#### 4.3.2 C++ 构建示例 (CMake)

```cmake
cmake_minimum_required(VERSION 3.13)
project(YOLO_ONNX)

set(CMAKE_CXX_STANDARD 11)

# 找到 OpenCV
find_package(OpenCV REQUIRED)

# 设置 ONNX Runtime 路径
set(ONNX_RUNTIME_DIR "path/to/onnxruntime")

include_directories(
    ${OpenCV_INCLUDE_DIRS}
    ${ONNX_RUNTIME_DIR}/include
)

link_directories(
    ${ONNX_RUNTIME_DIR}/lib
)

add_executable(yolo_onnx main.cpp)

target_link_libraries(yolo_onnx
    ${OpenCV_LIBS}
    onnxruntime
)
```

#### 4.4.3 编译和运行

```bash
# 创建构建目录
mkdir build && cd build

# 配置 CMake
cmake .. -DONNX_RUNTIME_DIR="path/to/onnxruntime"

# 编译
cmake --build .

# 运行
./yolo_onnx
```

## 5. 注意事项

### 5.1 模型规格说明

根据 `best.onnx` 文件的实际属性：

1. **输入规格**:
   - **名称**: `images`
   - **形状**: `[1, 3, 384, 640]` (批量大小1，3通道RGB，高度384，宽度640)
   - **数据类型**: `float32` (归一化到 [0, 1] 范围)
   - **预处理要求**: 输入图片需要缩放到 640×384 尺寸并转换为 RGB 格式

2. **输出规格**:
   - **名称**: `output0`
   - **形状**: `[1, 300, 6]` (批量大小1，最多300个检测框，每个框6个值)
   - **输出格式**: 每个检测框包含 `[x1, y1, x2, y2, confidence, class_id]`
   - **坐标范围**: 边界框坐标基于输入尺寸 (640×384) 的归一化值

3. **模型属性**:
   - **ONNX IR版本**: 8
   - **操作符数量**: 308 个
   - **模型格式**: ONNX 1.12.0
   - **文件大小**: 8.86 MB

### 5.2 推理环境要求

1. **执行提供者支持**:
   - **CPUExecutionProvider**: 默认可用，无需额外配置
   - **CUDAExecutionProvider**: 需要安装 CUDA 和 cuDNN
   - **TensorrtExecutionProvider**: 需要安装 TensorRT 库
   
   ```python
   # 使用示例
   import onnxruntime as ort
   # 使用 CPU
   session = ort.InferenceSession('best.onnx', providers=['CPUExecutionProvider'])
   # 使用 GPU (优先尝试 CUDA，失败后使用 CPU)
   session = ort.InferenceSession('best.onnx', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
   ```

2. **数值计算说明**:
   - 浮点计算可能存在微小的数值差异，这是正常现象
   - 确保使用一致的预处理步骤以获得稳定结果

### 5.3 部署注意事项

1. **输入一致性**: 确保预处理步骤符合模型输入要求
2. **输出解析**: 注意边界框坐标需要根据原始图像尺寸进行缩放
3. **内存管理**: 模型文件大小为 8.86 MB，加载到内存后占用约 15-25 MB，推理时需额外内存用于输入输出张量
4. **线程安全**: ONNX Runtime 会话支持多线程推理，但单个会话在不同线程间需同步访问

## 6. 故障排除

### 6.1 常见错误及解决方法

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|----------|
| `No such file or directory` | 模型或图片路径错误 | 检查路径是否正确 |
| `ONNX RuntimeError` | ONNX 模型损坏或版本不兼容 | 更新 ONNX Runtime 或获取有效的模型文件 |
| `CUDA out of memory` | GPU 内存不足 | 减小输入尺寸或使用 CPU |
| 未检测到任何目标 | 置信度阈值设置过高或图片中无目标 | 降低置信度阈值或检查图片内容 |

## 7. 结语

本 ONNX 模型是基于 YOLO 架构的目标检测模型。通过本文档提供的使用方法，您可以轻松地将模型集成到您的项目中，实现目标检测功能。

如果您在使用过程中遇到任何问题，请参考故障排除部分，或者在群里@tokutouseki
