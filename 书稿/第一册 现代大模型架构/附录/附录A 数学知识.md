# 附录A 数学知识
本附录跳过一般性的证明，重点关注和深度学习的联动

## 统计

### 均值方差

\(X,Y\) 为随机变量；\(a,b,c\) 为实常数。


定义期望（均值）：

\(\mathbb{E}[X]\)
定义方差：

\[
\mathrm{Var}(X)
= \mathbb{E}\left[(X-\mathbb{E}[X])^2\right]
= \mathbb{E}[X^2] - \big(\mathbb{E}[X]\big)^2
\]

协方差：

\[
\mathrm{Cov}(X,Y)
= \mathbb{E}[XY] - \mathbb{E}[X]\mathbb{E}[Y]
\]

> 
> 重要区分：
> \(\mathbb{E}[X^2]\) 是**先平方再取期望**；\((\mathbb{E}[X])^2\) 是**先取期望再平方**，二者一般不相等。

---

### 期望 性质

1. 常数期望：\(\mathbb{E}[c] = c\)
2. 线性性（无条件成立，不要求独立）

\(\mathbb{E}[aX + bY] = a\mathbb{E}[X] + b\mathbb{E}[Y]\)
推论：

\[
\mathbb{E}[X+Y]=\mathbb{E}[X]+\mathbb{E}[Y],\quad
\mathbb{E}[aX+b]=a\mathbb{E}[X]+b
\]

加法满足交换律，结合律。

3. 乘积期望（仅独立时成立）
若 \(X,Y\) 相互独立：

\(\mathbb{E}[XY] = \mathbb{E}[X]\cdot \mathbb{E}[Y]\)

---

### 方差性质

1. 线性伸缩平移

\(\mathrm{Var}(aX + b) = a^2\,\mathrm{Var}(X)\)
平移项 b 不改变方差；系数带平方，符号丢失：\(\mathrm{Var}(-aX)=\mathrm{Var}(aX)\)。

2. 和差通用公式（带协方差）

\[
\begin{aligned}
\mathrm{Var}(X+Y) &= \mathrm{Var}(X)+\mathrm{Var}(Y)+2\mathrm{Cov}(X,Y)\\
\mathrm{Var}(X-Y) &= \mathrm{Var}(X)+\mathrm{Var}(Y)-2\mathrm{Cov}(X,Y)
\end{aligned}
\]

若 \(X,Y\) 相互独立，则 \(\mathrm{Cov}(X,Y)=0\)：

\(\mathrm{Var}(X\pm Y) = \mathrm{Var}(X)+\mathrm{Var}(Y)\)

> 
> 关键结论：独立变量相减，方差依然相加，不是相减。

3. 加权和（两两独立）
若 \(X_1,X_2,\dots,X_n\) 两两独立：

\[
\mathrm{Var}\left(\sum_{i=1}^n a_i X_i\right)
=\sum_{i=1}^n a_i^2\,\mathrm{Var}(X_i)
\]

> 
> 说明：\(\mathrm{Var}(X+Y)=\mathrm{Var}(Y+X)\)，形式上加法交换成立；但方差算子**不是线性算子**，不能随意拆开。

---

## 协方差性质

1. 交换律：\(\mathrm{Cov}(X,Y)=\mathrm{Cov}(Y,X)\)
2. 双线性：\(\mathrm{Cov}(aX,bY)=ab\cdot\mathrm{Cov}(X,Y)\)
3. 自协方差：\(\mathrm{Cov}(X,X)=\mathrm{Var}(X)\)


### 均值方差与深度学习

1. **缩放点积注意力**
主运算：计算 \(QK^\top\) 得到 token 之间的原始内积相似度。
内积结果算出之后，除以 \(\sqrt{d}\)：

\(\frac{QK^\top}{\sqrt d}\)
向量维度 d 越大，原始内积的方差越高；这一步除法把内积的方差约束在 1 附近，防止 softmax 输出过度尖锐，梯度过小。

2. **AdamW 的偏置校正**
主运算：用指数移动平均累积梯度，得到一阶矩 \(m_t\)，二阶矩 \(v_t\)。
统计量计算完成后，做除法修正训练初期的估计偏差：

\(\hat m_t=\frac{m_t}{1-\beta_1^t},\quad \hat v_t=\frac{v_t}{1-\beta_2^t}\)
训练刚开始时动量估计值偏低，该除法校正统计量的均值偏差，得到更可靠的梯度估计。

3. **交叉熵的 Log-sum-exp 技巧**
主运算：计算 logits 的指数，用于 softmax。
指数运算之后，求和之前，减去最大值做整体平移：

\(\log\sum_i e^{z_i}=z_{\text{max}}+\log\sum_i e^{z_i-z_{\text{max}}}\)
指数函数极易发生数值溢出；减去最大值平移全部 logits，控制数值范围，稳定均值，保证计算可执行。

4. **Dropout**
训练前向：对激活施加随机 0/1 掩码 \(m\sim \text{Bernoulli}(r)\)，\(r=1-p\) 为保留概率

\(x_\text{train}=\frac{m\cdot x}{r}\)
推理阶段：无随机掩码，直接输出 \(x_\text{eval}=x\)。
掩码置零会压低输出均值，除以 r 做均值补偿，保证**训练输出的数学期望等于推理输出**。该操作只对齐一阶矩（均值），不会对齐方差

当然，还有很多这样的例子，你可以再思考几个



### HardMax
softmax 的名字来自两步：**max（取最大） + soft（柔和，平滑版本）**。我们先看硬max，再过渡到softmax。

给定一组数：`[2, 5, 3]`
硬max：直接挑最大的数字5，权重分配 `[0, 1, 0]`。
含义：只采信最大值对应的那一项，其余全部忽略。

### SoftMax

softmax 做平滑的概率分配

\[
\sigma(z_i)=\frac{e^{z_i}}{\sum_j e^{z_j}}.
\]

同样输入 `[2, 5, 3]`：

\[
e^{2}\approx 7.389,\quad
e^{5}\approx 148.413,\quad
e^{3}\approx 20.086.
\]

总和 \(7.389+148.413+20.086\approx 175.888\)。

- \(z_1=2\)：\(7.389/175.888\approx 0.042\)
- \(z_2=5\)：\(148.413/175.888\approx 0.844\)
- \(z_3=3\)：\(20.086/175.888\approx 0.114\)

输出：`[0.042, 0.844, 0.114]`，总和为 1。最大的值拿到最高权重，其余项仍保留一小部分。输出是概率分布：全部 \(\ge 0\)，总和等于 1。对比硬 max：它是平滑，可求导的选择，适合神经网络训练。

但是，softmax 是非线性运算，这带来两个底层难题。

第一，引入非线性后，式子不再满足矩阵乘法结合律，（线性函数和矩阵乘法 \(f(AB)C = A\,f(BC)\) ）在这里我们直接给出标准注意力表达式来看： \(\mathrm{softmax}(QK^\top)V\)。如果没有 softmax，表达式为 \((QK^\top)V\)，依据矩阵乘法结合律可重排为 \(Q(K^\top V)\)。两种计算顺序的代价对比如下：

> L 是输入序列的 token 长度，随文本变长而增大；d 是向量维度，属于模型固定常量，不随输入文本变化

- 顺序 1 \((QK^\top)V\)：先算 \(QK^\top\)。\(Q\)，\(K\) 形状都是 \([L,d]\)，相乘得到 \(L\times L\) 的相似度矩阵，这一步复杂度 \(O(L^{2}d)\)。序列长度 \(L\) 变大，算力按平方增长。
- 顺序 2 \(Q(K^\top V)\)：先算 \(K^\top V\)。\(K^\top\) 是 \([d,L]\)，\(V\) 是 \([L,d]\)，结果是 \(d\times d\) 的固定大小矩阵，复杂度只有 \(O(L d^{2})\)，随序列长度线性增长。无论文本多长，这一步的输出永远是 \(d\times d\)。

一旦插入 softmax，它作用在 \(QK^\top\) 得到的 \(L\times L\) 矩阵上。我们只能采用第一种昂贵计算顺序，必须完整算出全部 token 两两之间的相似度，复杂度 \(O(L^{2}d)\)。

第二，归一化引发注意力稀释。softmax 强制一行所有权重之和等于 1。当序列很长，一个 query 要分摊权重给大量 key，每个 key 分到的权重被摊薄。即便所有 token 全部参与计算，远距离 token 也很难拿到足够大的权重，难以建立远距离关联。

### 带温度的 softmax

把任意实数向量 \(z\in\mathbb{R}^{V}\) 变成概率分布：

\[
p_i
=
\frac{\exp(z_i/\tau)}
{\sum_j\exp(z_j/\tau)},
\qquad \tau>0.
\]

\(\tau=1\) 是标准 softmax。\(\tau\) 变大，分布变平；\(\tau\) 变小，质量更集中在最大的几项。第 1 章的采样和第 9 章的路由都用温度（或等价写法）控制尖锐程度。


### 交叉熵

自回归预训练的目标：给定前文 \(x_0,x_1,\dots,x_t\)，预测下一个 token \(x_{t+1}\)。
模型输出 logits：对每个序列位置，输出词表上的原始打分，未经过 Softmax。

\(\mathcal{L} = -\frac{1}{N}\sum_{t}\log p(x_{t+1}\mid x_0,\dots,x_t)\)张量约定

- \(\mathbf{\mathrm{logits}} \in \mathbb{R}^{B\times T\times V}\)：三维张量。B 批次，T 序列长度，V 词表大小。每个位置输出全部词表候选的浮点打分。
- \(\mathbf{\mathrm{targets}} \in \mathbb{Z}^{B\times T}\)：二维张量，**无词表维度**。每个位置仅保存一个真实 token 的整数索引，不是 one‑hot。`CrossEntropyLoss` 原生支持类别索引标签。

移位对齐规则
原始序列 \([x_0,x_1,\dots,x_{T-1}]\)。
用位置 \(0,\dots,T-2\) 的 logits，预测位置 \(1,\dots,T-1\) 的目标 token：

- \(\mathrm{logits}[:,:-1,:]\)：取前 \(T-1\) 个预测位置
- \(\mathrm{targets}[:,1:]\)：取后 \(T-1\) 个作为对应的预测标签

```python 
    import torch
    import torch.nn as nn

    B = 2    # batch size
    T = 1024 # sequence length
    V = 32000 # vocab size

    # logits：浮点打分，randn 入参直接为维度
    logits = torch.randn(B, T, V)
    # targets：token整数编号，使用关键字参数显式区分值域与shape
    targets = torch.randint(low=0, high=V, size=(B, T))

    # next-token移位
    shift_logits = logits[:, :-1, :].contiguous()  # [B, T-1, V]
    shift_targets = targets[:, 1:].contiguous()    # [B, T-1]

    loss_fn = nn.CrossEntropyLoss(ignore_index=-100)
    loss = loss_fn(
        shift_logits.view(-1, V),
        shift_targets.view(-1)
    )
```

`nn.CrossEntropyLoss` 内部包含 LogSoftmax + NLLLoss

设单样本 logit 向量 \(\mathbf{z}\in\mathbb{R}^{V}\)，真实类别索引为 \(y\)。

1. LogSoftmax

\[
\log p_i = \mathrm{LogSoftmax}(z_i)
= \log\left( \frac{e^{z_i}}{\sum_{k=1}^V e^{z_k}} \right)
\]

输出每个类别的**对数概率**。

2. NLLLoss（负对数似然损失）

\(\mathrm{NLLLoss}(\log p, y) = -\log p_y\)
只取出真实类别位置的对数概率，取负。

合并起来，就是 CrossEntropyLoss：

\[
\mathrm{CrossEntropy}(z,y)
= -\log\left( \frac{e^{z_y}}{\sum_{k=1}^V e^{z_k}} \right)
\]

这里交叉熵拆成两部分主要是因为：

1. **数值稳定性**
直接先算 softmax 再取 log 容易出现上溢；`LogSoftmax` 实现时用 \(\max(z)\) 做平移归一，在 log 域计算，减少浮点爆炸。
2. **接口复用**
NLLLoss 接收对数概率输入。如果你自己通过别的方式算出对数概率（比如模型直接输出 log-prob），可以直接喂给 NLLLoss，不需要重复 softmax。
3. **梯度等价**
合并与拆分的梯度完全一样，只是封装形式不同。

> 注意：不要在 logits 外面手动套 Softmax 再送入 CrossEntropyLoss，等价于多做一次 softmax，结果完全错误。


### 散度

两个离散分布 \(p,q\) 的 KL 散度：

\[
D_{\mathrm{KL}}(p\|q)
=
\sum_i p_i\log\frac{p_i}{q_i}.
\]

它非负，且仅当 \(p=q\) 时为 0。衡量的是用 \(q\) 去编码来自 \(p\) 的样本时多付的代价；不对称，\(D_{\mathrm{KL}}(p\|q)\) 与 \(D_{\mathrm{KL}}(q\|p)\) 一般不相等。