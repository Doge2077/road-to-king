# import torch
# import torch.nn as nn
#
# # 定义 logits 和真实标签（注意：这里 y 是类别索引，不是 one-hot）
# z = torch.tensor([[2.0, 1.0, 0.1]], dtype=torch.float32)  # 必须是 2D (batch_size, num_classes)
# y = torch.tensor([1], dtype=torch.long)  # 类别索引（1 表示第2类）
#
# # 使用 nn.CrossEntropyLoss（自动包含 Softmax + 交叉熵）
# criterion = nn.CrossEntropyLoss()
# loss = criterion(z, y)
#
# print("Logits:", z)
# print("真实类别:", y.item())  # 1
# print("交叉熵损失:", loss.item())  # ≈1.418

# import torch
# import torch.nn as nn
#
# # 定义 logit 和真实标签
# z = torch.tensor([0.8], dtype=torch.float32)  # 注意是 1D 或 2D
# y = torch.tensor([1.0], dtype=torch.float32)  # 二分类标签必须是浮点数
#
# # 使用 nn.BCEWithLogitsLoss（内置 Sigmoid + 交叉熵）
# criterion = nn.BCEWithLogitsLoss()
# loss = criterion(z, y)
#
# print("Logit:", z.item())  # 0.8
# print("真实标签:", y.item())  # 1
# print("Sigmoid 概率:", torch.sigmoid(z).item())  # ≈0.690
# print("二元交叉熵损失:", loss.item())  # ≈0.371

# import torch
# import torch.nn as nn
#
# # 真实值和预测值（假设 batch_size=4）
# y_true = torch.tensor([3.0, -0.5, 2.0, 7.0])
# y_pred = torch.tensor([2.5, 0.0, 2.0, 8.0])
#
# # 使用 PyTorch 的 L1Loss（即 MAE）
# criterion = nn.L1Loss()
# loss = criterion(y_pred, y_true)
#
# print("MAE 损失:", loss.item())  # 输出 0.5

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

# 设置中文字体（推荐使用系统已安装的中文字体）
rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']  #
rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

x = np.linspace(-3, 3, 500)
mse = x**2
mae = np.abs(x)
smooth_l1 = np.where(np.abs(x)<1, 0.5*x**2, np.abs(x)-0.5)

plt.figure(figsize=(12, 7))

# 绘制曲线
plt.plot(x, mse, label='MSE', linewidth=3, color='royalblue')
plt.plot(x, mae, label='MAE', linewidth=3, color='forestgreen')
plt.plot(x, smooth_l1, label='Smooth L1 (beta=1)', linewidth=3, color='crimson')

# 添加阴影区域
plt.fill_between(x, mse, smooth_l1, where=(x>1),
                color='salmon', alpha=0.3, label='MSE惩罚更强区域')
plt.fill_between(x, mae, smooth_l1, where=(np.abs(x)<1),
                color='lightgreen', alpha=0.3, label='SmoothL1平滑过渡区')
plt.fill_between(x, mae, smooth_l1, where=(np.abs(x)>1),
                color='skyblue', alpha=0.3, label='线性处理区')

# 添加阈值标记
plt.axvline(1, color='gray', linestyle='--', alpha=0.5)
plt.axvline(-1, color='gray', linestyle='--', alpha=0.5)
plt.text(1.05, 5, 'Beta=1阈值', rotation=90, va='center')

# 图表装饰
plt.legend(fontsize=12, loc='upper center')
plt.xlabel('预测误差 (y_true - y_pred)', fontsize=12)  # 中文标签
plt.ylabel('损失值', fontsize=12)  # 中文标签
plt.title('回归损失函数对比\n(阴影区域突出关键差异)',
         fontsize=14, pad=20)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xlim(-3, 3)
plt.ylim(0, 9)

plt.tight_layout()
plt.savefig('loss_comparison.png', dpi=300, bbox_inches='tight')  # 保存时确保完整显示
plt.show()