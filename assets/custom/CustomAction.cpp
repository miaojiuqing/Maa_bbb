// // src/CustomAction.cpp
// // #include "CustomAction.h"
// // #include <MaaFramework/Controller/ControllerAgent.hpp>
// // #include <MaaFramework/Utils/Sleep.hpp>
// #include <iostream>
// #include <random>
// #include <unordered_map>

// namespace MaaNS {

// // 存储所有自定义动作的映射表
// static std::unordered_map<std::string, CustomActionManager::ActionHandler> custom_actions_map;

// // ==================== 工具函数 ====================

// // 获取随机偏移
// int get_random_offset(int center, int offset) {
//     if (offset <= 0) return center;
    
//     static std::random_device rd;
//     static std::mt19937 gen(rd());
//     std::uniform_int_distribution<> dis(-offset, offset);
//     return center + dis(gen);
// }

// // 带随机偏移的点击
// bool click_with_random_offset(ControllerAgentPtr controller, int x, int y, int offset) {
//     int rand_x = get_random_offset(x, offset);
//     int rand_y = get_random_offset(y, offset);
//     return controller->click(rand_x, rand_y);
// }

// // ==================== 管理器实现 ====================

// void CustomActionManager::register_action(const std::string& name, ActionHandler handler) {
//     custom_actions_map[name] = handler;
//     std::cout << "Registered custom action: " << name << std::endl;
// }

// bool CustomActionManager::execute_action(const std::string& name, const json& param, ControllerAgentPtr controller) {
//     auto it = custom_actions_map.find(name);
//     if (it != custom_actions_map.end()) {
//         try {
//             return it->second(param, controller);
//         } catch (const std::exception& e) {
//             std::cerr << "Error executing custom action '" << name << "': " << e.what() << std::endl;
//             return false;
//         }
//     }
//     std::cerr << "Custom action not found: " << name << std::endl;
//     return false;
// }

// bool CustomActionManager::has_action(const std::string& name) {
//     return custom_actions_map.find(name) != custom_actions_map.end();
// }

// // ==================== 自定义动作实现 ====================

// // 1. 基础快速双击
// void register_double_click() {
//     CustomActionManager::register_action(
//         "double_click",
//         [](const json& param, ControllerAgentPtr controller) -> bool {
//             try {
//                 int x = param.value("point", json::array({0, 0}))[0];
//                 int y = param.value("point", json::array({0, 0}))[1];
//                 int interval = param.value("interval", 50);
                
//                 // 第一次点击
//                 if (!controller->click(x, y)) {
//                     std::cerr << "First click failed" << std::endl;
//                     return false;
//                 }
                
//                 // 等待间隔
//                 MaaNS::sleep(interval);
                
//                 // 第二次点击
//                 if (!controller->click(x, y)) {
//                     std::cerr << "Second click failed" << std::endl;
//                     return false;
//                 }
                
//                 return true;
//             } catch (const std::exception& e) {
//                 std::cerr << "Double click error: " << e.what() << std::endl;
//                 return false;
//             }
//         }
//     );
// }

// // 2. 带随机偏移的双击
// void register_double_click_random() {
//     CustomActionManager::register_action(
//         "double_click_random",
//         [](const json& param, ControllerAgentPtr controller) -> bool {
//             try {
//                 int x = param.value("point", json::array({0, 0}))[0];
//                 int y = param.value("point", json::array({0, 0}))[1];
//                 int interval = param.value("interval", 50);
//                 int offset = param.value("offset", 5);
                
//                 // 第一次点击（带随机偏移）
//                 if (!click_with_random_offset(controller, x, y, offset)) {
//                     return false;
//                 }
                
//                 // 等待间隔
//                 MaaNS::sleep(interval);
                
//                 // 第二次点击（带随机偏移）
//                 if (!click_with_random_offset(controller, x, y, offset)) {
//                     return false;
//                 }
                
//                 return true;
//             } catch (const std::exception& e) {
//                 std::cerr << "Random double click error: " << e.what() << std::endl;
//                 return false;
//             }
//         }
//     );
// }

// // 3. 多点双击序列
// void register_double_click_sequence() {
//     CustomActionManager::register_action(
//         "double_click_sequence",
//         [](const json& param, ControllerAgentPtr controller) -> bool {
//             try {
//                 auto points = param.value("points", json::array());
//                 int interval = param.value("interval", 50);
//                 int delay_between = param.value("delay_between", 200);
//                 int offset = param.value("offset", 0);
                
//                 if (points.empty()) {
//                     std::cerr << "No points provided for sequence" << std::endl;
//                     return false;
//                 }
                
//                 for (size_t i = 0; i < points.size(); ++i) {
//                     const auto& point = points[i];
//                     int x = point[0];
//                     int y = point[1];
                    
//                     // 双击当前点
//                     if (offset > 0) {
//                         if (!click_with_random_offset(controller, x, y, offset)) return false;
//                         MaaNS::sleep(interval);
//                         if (!click_with_random_offset(controller, x, y, offset)) return false;
//                     } else {
//                         if (!controller->click(x, y)) return false;
//                         MaaNS::sleep(interval);
//                         if (!controller->click(x, y)) return false;
//                     }
                    
//                     // 如果不是最后一个点，等待间隔
//                     if (i < points.size() - 1) {
//                         MaaNS::sleep(delay_between);
//                     }
//                 }
                
//                 return true;
//             } catch (const std::exception& e) {
//                 std::cerr << "Double click sequence error: " << e.what() << std::endl;
//                 return false;
//             }
//         }
//     );
// }

// // 4. 基于识别结果的双击
// void register_double_click_at_match() {
//     CustomActionManager::register_action(
//         "double_click_at_match",
//         [](const json& param, ControllerAgentPtr controller) -> bool {
//             try {
//                 int interval = param.value("interval", 50);
//                 int offset = param.value("offset", 0);
//                 std::string target_name = param.value("target", "");
                
//                 // 获取识别结果
//                 auto recognition_result = controller->get_last_recognition_result();
//                 if (!recognition_result.valid) {
//                     std::cerr << "No valid recognition result" << std::endl;
//                     return false;
//                 }
                
//                 if (!target_name.empty() && recognition_result.name != target_name) {
//                     std::cerr << "Recognition target mismatch: expected " << target_name 
//                               << ", got " << recognition_result.name << std::endl;
//                     return false;
//                 }
                
//                 int center_x = recognition_result.rect.center_x();
//                 int center_y = recognition_result.rect.center_y();
                
//                 // 执行双击
//                 if (offset > 0) {
//                     if (!click_with_random_offset(controller, center_x, center_y, offset)) return false;
//                     MaaNS::sleep(interval);
//                     if (!click_with_random_offset(controller, center_x, center_y, offset)) return false;
//                 } else {
//                     if (!controller->click(center_x, center_y)) return false;
//                     MaaNS::sleep(interval);
//                     if (!controller->click(center_x, center_y)) return false;
//                 }
                
//                 return true;
//             } catch (const std::exception& e) {
//                 std::cerr << "Double click at match error: " << e.what() << std::endl;
//                 return false;
//             }
//         }
//     );
// }

// // 5. 三重点击
// void register_triple_click() {
//     CustomActionManager::register_action(
//         "triple_click",
//         [](const json& param, ControllerAgentPtr controller) -> bool {
//             try {
//                 int x = param.value("point", json::array({0, 0}))[0];
//                 int y = param.value("point", json::array({0, 0}))[1];
//                 int interval = param.value("interval", 40);
//                 int offset = param.value("offset", 3);
                
//                 for (int i = 0; i < 3; i++) {
//                     if (offset > 0) {
//                         if (!click_with_random_offset(controller, x, y, offset)) return false;
//                     } else {
//                         if (!controller->click(x, y)) return false;
//                     }
                    
//                     if (i < 2) {
//                         MaaNS::sleep(interval);
//                     }
//                 }
                
//                 return true;
//             } catch (const std::exception& e) {
//                 std::cerr << "Triple click error: " << e.what() << std::endl;
//                 return false;
//             }
//         }
//     );
// }

// // ==================== 主注册函数 ====================

// void register_custom_actions() {
//     std::cout << "Starting custom actions registration..." << std::endl;
    
//     // 注册所有自定义动作
//     register_double_click();
//     register_double_click_random();
//     register_double_click_sequence();
//     register_double_click_at_match();
//     register_triple_click();
    
//     std::cout << "Custom actions registration complete. Total actions: " 
//               << custom_actions_map.size() << std::endl;
    
//     // 输出已注册的动作列表
//     std::cout << "Registered actions: ";
//     for (const auto& pair : custom_actions_map) {
//         std::cout << pair.first << " ";
//     }
//     std::cout << std::endl;
// }

// } // namespace MaaNS

// // ==================== MAA插件入口点 ====================

// extern "C" {
    
//     MAA_PLUGIN_EXPORT void MaaPluginInit() {
//         std::cout << "MAA Custom Actions Plugin Initializing..." << std::endl;
//         MaaNS::register_custom_actions();
//         std::cout << "MAA Custom Actions Plugin Initialized Successfully" << std::endl;
//     }
    
//     MAA_PLUGIN_EXPORT void MaaPluginUninit() {
//         std::cout << "MAA Custom Actions Plugin Uninitializing..." << std::endl;
//         // 清理资源
//         std::cout << "MAA Custom Actions Plugin Uninitialized" << std::endl;
//     }
    
//     MAA_PLUGIN_EXPORT const char* MaaPluginName() {
//         return "MaaCustomActions";
//     }
    
//     MAA_PLUGIN_EXPORT const char* MaaPluginVersion() {
//         return "1.0.0";
//     }
// }