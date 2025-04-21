import torch
import torch.nn as nn
from torchsummary import summary  # 计算模型参数，查看模型结构


# 创建神经网络模型类
class Model(nn.Module):
    # 初始化属性值
    def __init__(self):
        super(Model, self).__init__()  # 调用父类的初始化属性值
        # 创建第一个隐藏层模型，3个输入特征，3个输出特征
        self.linear1 = nn.Linear(3, 3)
        # 初始化权重 - 标准化的Xavier初始化
        nn.init.xavier_normal_(self.linear1.weight)

        # 创建第二个隐藏层模型，3个输入特征（上一层的输出特征），2个输出特征
        self.linear2 = nn.Linear(3, 2)
        # 初始化权重 - He初始化
        nn.init.kaiming_normal_(self.linear2.weight)

        # 创建输出层模型
        self.out = nn.Linear(2, 2)

    # 创建前向传播方法，自动执行forward()方法
    def forward(self, x):
        # 数据经过第一个线性层
        x = self.linear1(x)
        # 使用sigmoid激活函数
        x = torch.sigmoid(x)

        # 数据经过第二个线性层
        x = self.linear2(x)
        # 使用relu激活函数
        x = torch.relu(x)  # 注意：这里应该是torch.relu(x)，原代码有拼写错误

        # 数据经过输出层
        x = self.out(x)
        # 使用softmax激活函数
        # dim=-1: 每一维度行数据相加为1
        x = torch.softmax(x, dim=-1)

        return x


if __name__ == '__main__':

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('current device:', device)

    # 实例化model对象
    my_model = Model().to(device)

    # 随机产生数据
    my_data = torch.randn(5, 3).to(device)  # 5个样本，每个样本3个特征
    print("my_data shape:", my_data.shape)

    # 数据经过神经网络模型训练
    output = my_model(my_data)
    print("output shape->", output.shape)

    # 计算模型参数
    # 计算每层每个神经元的w和b个数总和
    summary(my_model, input_size=(3,), batch_size=5, device=str(device))

    # 查看模型参数
    print("查看模型参数w和b:")
    for name, parameter in my_model.named_parameters():
        print(name, parameter)

