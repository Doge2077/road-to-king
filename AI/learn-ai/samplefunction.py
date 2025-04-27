import torch
import torch.nn as nn
import torch.optim as optim

# 模型定义
model = nn.Linear(2, 1)
# 损失函数 MSE
criterion = nn.MSELoss()
# 梯度下降 SGD
optimizer = optim.SGD(model.parameters(), lr=0.01)

# 数据集
X = torch.randn(1000, 2)  # 1000个样本
y = torch.randn(1000, 1)

# BGD训练
for epoch in range(100):
    # 前向传播（全部数据）
    outputs = model(X)
    loss = criterion(outputs, y)

    # 反向传播
    optimizer.zero_grad()
    loss.backward()

    # 更新参数
    optimizer.step()

    if (epoch + 1) % 10 == 0:
        print(f'Epoch [{epoch + 1}/100], Loss: {loss.item():.4f}')