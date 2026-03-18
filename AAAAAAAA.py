# a = 13
# b = 34
# a = a + b
# b = a - b
# a = a - b
# print(a, b)
# range(10)

# a = 2
# a**= 3//2 的三次方
# print(a)

# a = 0# 初始化变量 a 为 1（阶乘的初始值应为 1）
# for i in (1, 2, 3, 4, 5):# 使用 for 循环遍历数字 1 到 5
#     a *= i # 累乘计算阶乘
# print(a)# 输出 5 的阶乘结果：1×2×3×4×5 = 120

# def a(b):           # 定义函数 a，参数为 b
#     try:            # 尝试执行下面的操作
#         return b*5  # 返回 b 乘以 5 的结果
#     except:         # 如果上面操作出错（比如 b 不是数字）
#         return b    # 就返回 b 本身

# print(a("1"))       # 调用函数 a，传入字符串"1"，输出结果



# # 定义一个二维列表，包含 3 个子列表，每个子列表有 2 个元素
# ls = [[0,1],[5,6],[7,8]]# 创建一个空列表，用于存储提取出来的元素
# lis = []
# # 使用 for 循环遍历二维列表 ls 的索引范围 (0, 1, 2)
# # range(len(ls)) 生成从 0 到 2 的整数序列
# for i in range(len(ls)):
#     # ls[i] 表示访问第 i 个子列表
#     # ls[i][1] 表示访问第 i 个子列表中索引为 1 的元素（即第二个元素）
#     # append() 方法将提取到的元素添加到 lis 列表末尾
#     lis.append(ls[i][1])

# # 输出最终的列表结果：[1, 6, 8]
# print(lis)

# def f(n):
#     if n == 1:
#         return 1
#     else:
#         return n*f(n-1)
# print(f(4))
x=3
x*=6
print(x)
                