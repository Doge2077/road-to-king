import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import make_regression
from torch.utils.data import DataLoader, TensorDataset


# 创建数据集
def create_dataset():
    x, y, coef = make_regression(n_samples=100, n_features=1, noise=10, coef=True, bias=1.5, random_state=0)
    # 将构建的数据转换为张量类型
    x = torch.tensor(x, dtype=torch.float32)
    y = torch.tensor(y, dtype=torch.float32)
    coef = torch.tensor(coef, dtype=torch.float32)  # 将 coef 转换为 torch 张量
    return x, y, coef


# 可视化数据集
def plot_data(x, y, coef):
    plt.scatter(x, y)
    x_line = torch.linspace(x.min(), x.max(), 1000)
    # 使用 torch 操作替代列表推导
    y_line = coef * x_line + 1.5
    plt.plot(x_line, y_line, label='Real Line')
    plt.grid()
    plt.legend()
    plt.show()


# 生成数据
x, y, coef = create_dataset()

# 可视化真实的线性回归结果
plot_data(x, y, coef)

# 构造数据集和数据加载器
dataset = TensorDataset(x, y)
dataloader = DataLoader(dataset, batch_size=16, shuffle=True)

# 构造线性回归模型
model = nn.Linear(in_features=1, out_features=1)

# 构造平方损失函数
criterion = nn.MSELoss()

# 构造优化器
optimizer = optim.SGD(params=model.parameters(), lr=1e-2)

# 训练周期
epochs = 100
epoch_loss = []

# 训练模型
for epoch in range(epochs):
    total_loss = 0.0
    train_sample = 0.0
    for train_x, train_y in dataloader:
        # 将一个batch的训练数据送入模型
        y_pred = model(train_x)
        # 计算损失值
        loss = criterion(y_pred, train_y.reshape(-1, 1))
        total_loss += loss.item()
        train_sample += len(train_y)

        # 梯度清零
        optimizer.zero_grad()
        # 反向传播
        loss.backward()
        # 更新参数
        optimizer.step()

    epoch_loss.append(total_loss / train_sample)

# 绘制损失变化曲线
plt.plot(range(epochs), epoch_loss)
plt.title('Loss Curve')
plt.grid()
plt.show()

# 可视化拟合直线
plt.scatter(x, y)
x_line = torch.linspace(x.min(), x.max(), 1000)
y_pred_line = model(x_line.reshape(-1, 1)).detach().numpy()
# 使用 torch 操作替代列表推导
y_true_line = coef * x_line + 1.5  # 使用 torch 操作
plt.plot(x_line, y_pred_line, label='Predicted Line')
plt.plot(x_line, y_true_line.numpy(), label='True Line')  # 转换为 NumPy 数组
plt.grid()
plt.legend()
plt.show()
