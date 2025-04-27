import torch
import matplotlib.pyplot as plt

ELEMENT_NUMBER = 30  # 定义元素数量为30

# 1. 实际平均温度
def dayTemperature():
    # 固定随机数种子
    torch.manual_seed(0)
    # 产生30天的随机温度，范围在10左右波动
    temperature = torch.randn(size=[ELEMENT_NUMBER,]) * 10
    print(temperature)
    # 绘制平均温度
    days = torch.arange(1, ELEMENT_NUMBER + 1, 1)
    plt.plot(days, temperature, color='r', label='Daily Temperature')
    plt.scatter(days, temperature)
    plt.xlabel('Day')
    plt.ylabel('Temperature')
    plt.title('Actual Daily Temperature')
    plt.legend()
    plt.show()

# 2. 指数移动平均温度
def EMATemperature(beta=0.9):
    torch.manual_seed(0)  # 固定随机数种子
    temperature = torch.randn(size=[ELEMENT_NUMBER,]) * 10  # 产生30天的随机温度
    exp_weight_avg = []
    for idx, temp in enumerate(temperature, 1):  # 从下标1开始（实际是第0天）
        # 第一个元素的EMA值等于自身
        if idx == 1:
            exp_weight_avg.append(temp)
            continue
        # 后续元素的EMA值等于上一个EMA乘以beta + 当前气温乘以(1-beta)
        new_temp = exp_weight_avg[idx - 2] * beta + (1 - beta) * temp
        exp_weight_avg.append(new_temp)
    days = torch.arange(1, ELEMENT_NUMBER + 1, 1)
    plt.plot(days, exp_weight_avg, color='b', label='EMA Temperature')
    plt.scatter(days, temperature, color='r', label='Daily Temperature')
    plt.xlabel('Day')
    plt.ylabel('Temperature')
    plt.title(f'Exponential Moving Average (beta={beta})')
    plt.legend()
    plt.show()

# 测试
dayTemperature()  # 绘制实际温度
EMATemperature()  # 绘制EMA温度（默认beta=0.9）
EMATemperature(beta=0.5)  # 绘制EMA温度（beta=0.5）