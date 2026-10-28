# 第 9 章 混合专家模型

第 8 章的一层里，注意力之后接一块 SwiGLU。对每个 token，SwiGLU 都要完成门控投影，升维投影和降维投影：

\[
\operatorname{SwiGLU}(x)
=W_{\mathrm{down}}
\left[
\operatorname{SiLU}(W_{\mathrm{gate}}x)
\odot(W_{\mathrm{up}}x)
\right].
\]

混合专家模型（Mixture of Experts，MoE）在同一层里放入多块 SwiGLU，每一块称为一个**专家**。输入到达 FFN 支路时，路由器先选出少数专家，选中的专家完成计算，其余专家保持空闲。

设一层有 \(N\) 个专家，每个 token 选 \(k\) 个，且 \(k\ll N\)。专家总参数随 \(N\) 增长；一个 token 的专家计算量只随 \(k\) 增长。现代大模型由此获得数百 B 的总参数，同时把单 token 激活量控制在数十 B。

## 9.1 专家层

设隐藏宽度为 \(d\)，单个专家记为

\[
E_i:\mathbb{R}^{d}\rightarrow\mathbb{R}^{d},
\qquad i=1,\ldots,N.
\]

\(E_i\) 内部采用 SwiGLU，输入，输出形状都是 \(d\)。不同专家拥有独立参数，训练后形成不同的变换。

路由器是一块线性层：

\[
s=W_rx,\qquad W_r\in\mathbb{R}^{N\times d}.
\]

输入 \(x\in\mathbb{R}^{d}\) 经过路由器后得到 \(N\) 个分数

\[
s=(s_1,s_2,\ldots,s_N).
\]

取其中最大的 \(k\) 项，其下标构成专家集合

\[
\mathcal T(x)=\operatorname{TopK}(s,k).
\]

选中专家的输出按路由权重相加：

\[
\operatorname{MoE}(x)
=
\sum_{i\in\mathcal T(x)}
g_i(x)E_i(x).
\]

对选中的 \(k\) 个分数做 softmax：

\[
g_i(x)
=
\frac{\exp(s_i)}
{\sum_{j\in\mathcal T(x)}\exp(s_j)},
\qquad i\in\mathcal T(x).
\]

因此 \(\sum_i g_i=1\)。权重较大的专家对当前 token 的输出影响更大。

设 \(N=4,k=2\)，某个 token 的路由分数为

\[
s=(1.0,\,3.0,\,0.2,\,2.0).
\]

分数最高的是专家 1 和专家 3（下标从 0 开始）。对 \((3.0,2.0)\) 做 softmax，得到约 \((0.73,0.27)\)，这一层的输出为

\[
y\approx0.73E_1(x)+0.27E_3(x).
\]

专家 0 和专家 2 不参与这个 token 的前向。下一个 token 会产生另一组路由分数，也可能选择另一组专家。路由以 token 为单位，同一条序列中的相邻 token 可以走不同专家。

## 9.2 路由

语言模型的交叉熵沿专家输出反向传播。选中的专家收到梯度，其参数逐渐适合被分配给自己的 token。混合权重 \(g_i\) 依赖路由分数 \(s_i\)，路由器 \(W_r\) 也会收到梯度。

top-\(k\) 产生离散下标。反向传播固定本次已经选中的专家，在这些分数之间优化混合比例；本次落选的专家没有经过输出路径，也没有来自这个 token 的专家梯度。

训练一段时间后，专家往往形成可观察的分工。部分专家更常处理代码，数字或特定语言，部分专家更偏向标点，连接词等高频模式。这种分工由数据与优化过程共同形成，训练目标没有给专家预先命名。

\(k\) 决定每个 token 同时使用多少专家：

- \(k=1\)：每个 token 只进入一个专家，专家计算量最低。
- \(k=2\)：两个专家共同产生输出，Mixtral 等模型采用过这一设定。
- 更大的 \(k\)：组合能力增加，专家计算量和通信量也随之增长。

有些模型还设置**共享专家**。共享专家绕过 top-\(k\)，每个 token 都会经过它们；路由专家承担其余的差异化计算。设共享专家数为 \(n_{\mathrm{shared}}\)，单个专家参数量为 \(P_E\)，则 FFN 部分的单 token 激活参数近似为

\[
P_{\mathrm{active,ffn}}
\approx
(k+n_{\mathrm{shared}})P_E.
\]

## 9.3 负载均衡

路由分配容易出现正反馈：某个专家在训练初期略占优势，收到的 token 增多，参数更新更充分，之后又得到更多 token。最终少数专家承担大部分输入，其余专家很少更新。此时模型虽然存着 \(N\) 份专家参数，实际利用的容量却小得多；多卡训练还会因为少数设备过载而等待。

负载均衡约束路由分布，使各专家获得相近数量的 token。

### 辅助损失

记一个 batch 中发给专家 \(i\) 的 token 比例为 \(f_i\)，路由器分给专家 \(i\) 的平均概率为 \(p_i\)。常见的均衡项为

\[
\mathcal L_{\mathrm{balance}}
=
\alpha N\sum_{i=1}^{N}f_ip_i.
\]

训练使用

\[
\mathcal L
=
\mathcal L_{\mathrm{LM}}
+
\mathcal L_{\mathrm{balance}}.
\]

当分配接近均匀时，\(f_i\) 与 \(p_i\) 都接近 \(1/N\)。某个专家同时具有较高路由概率和较高 token 占比时，均衡项增大。\(\alpha\) 控制均衡强度：取值过小，专家仍可能拥挤；取值过大，路由器会为了均匀而牺牲语言模型目标。

### 专家容量

设当前 batch 共含 \(T\) 个 token，每个 token 选择 \(k\) 个专家。平均每个专家接收 \(Tk/N\) 次分配。容量因子 \(c\) 给出专家上限：

\[
C
=
\left\lceil
c\frac{Tk}{N}
\right\rceil.
\]

超过 \(C\) 的分配会被丢弃或转交给其他专家。固定容量便于预分配显存和组织通信，同时会使部分 token 少一次专家计算。

### 选择偏置

免辅助损失的方法为每个专家维护一个偏置 \(b_i\)。选择专家时使用

\[
\mathcal T(x)
=
\operatorname{TopK}(s+b,k),
\]

混合权重仍由原始分数 \(s\) 计算。一次统计结束后，根据实际负载更新偏置：

\[
b_i
\leftarrow
b_i+\eta\,
\operatorname{sign}(\bar f-f_i).
\]

负载高于均值的专家降低偏置，负载低于均值的专家提高偏置。偏置只参与专家选择，不参与梯度优化。DeepSeek-V3 使用了这一类方法，使语言模型损失中无需加入较强的均衡项。

当专家数量很大，每个 token 只选极少专家时，负载统计波动更强。更新步长 \(\eta\)，统计窗口和初始路由分布都会影响稳定性。

## 9.4 细粒度专家

专家数量和单个专家宽度可以互相调节。早期常见的配置是少量大专家，例如 8 个专家选 2 个。细粒度 MoE 把每个大专家拆成多个较窄专家，同时增加 \(N\) 与 \(k\)。

设原来每个专家参数量为 \(P_E\)。拆成 \(m\) 个较小专家后，单个专家约为 \(P_E/m\)。每个 token 同时选择更多小专家，可以维持相近的激活参数量，并得到更多专家组合。DeepSeekMoE，Qwen3-MoE 都采用了细粒度专家与共享专家。

FFN 部分的总参数近似为

\[
P_{\mathrm{total,ffn}}
\approx
(N+n_{\mathrm{shared}})P_E,
\]

激活参数近似为

\[
P_{\mathrm{active,ffn}}
\approx
(k+n_{\mathrm{shared}})P_E.
\]

整网还要加上注意力，嵌入，输出头和路由器。

## 9.5 总参数与激活参数

MoE 模型同时报告两个参数量：

| 指标 | 内容 | 主要影响 |
|---|---|---|
| 总参数 \(P_{\mathrm{total}}\) | 全部专家与公共模块 | 权重显存，模型容量 |
| 激活参数 \(P_{\mathrm{active}}\) | 一个 token 实际经过的专家与公共模块 | 单 token FLOPs，Decode 成本 |

例如专家部分有 \(N=64\) 个专家，每个 token 选 \(k=8\) 个，忽略共享专家与公共模块时，总参是激活参数的 8 倍。加入始终激活的注意力，嵌入和共享专家后，整网比例会低于 8 倍。

这套结构把旗舰模型推进到数百 B 总参数，同时将每 token 激活量维持在数十 B。所有专家权重仍须存放，训练与部署通常需要专家并行；路由后的 token 要在设备间重新分发；每个专家收到的 token 数还要足够大，矩阵乘才能高效运行。

大 batch 会覆盖更多专家。虽然每个 token 仍只计算 \(k\) 个专家，一个 batch 可能读取几乎全部专家权重，因此实际延迟不能直接按 \(k/N\) 缩放。

## 9.6 代码

代码从第 8 章的 `SwiGLU` 开始。单个专家保留相同的三块投影。`MoESwiGLU` 增加路由器，专家列表，共享专家和选择偏置。

输入 `x` 的形状为 `[B,n,d]`。实现先把 batch 与序列维合并为 `[T,d]`，其中 \(T=B\times n\)。路由器一次得到 `[T,N]` 的分数表。随后按专家编号收集 token，使同一专家一次处理一小批输入。

```python
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class MoEConfig:
    n_embd: int = 128
    n_ff: int = 128          # 单个专家的中间维
    n_experts: int = 8
    n_experts_per_tok: int = 2
    n_shared_experts: int = 1
    route_scale: float = 1.0


class SwiGLUExpert(nn.Module):
    """与第 8 章 SwiGLU 相同的三块投影。"""

    def __init__(self, d_model: int, d_ff: int):
        super().__init__()
        self.gate_proj = nn.Linear(d_model, d_ff, bias=False)
        self.up_proj = nn.Linear(d_model, d_ff, bias=False)
        self.down_proj = nn.Linear(d_ff, d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class MoESwiGLU(nn.Module):
    def __init__(self, cfg: MoEConfig):
        super().__init__()
        if not (1 <= cfg.n_experts_per_tok <= cfg.n_experts):
            raise ValueError("n_experts_per_tok 需落在 1..n_experts")
        self.cfg = cfg
        self.router = nn.Linear(cfg.n_embd, cfg.n_experts, bias=False)
        self.experts = nn.ModuleList(
            SwiGLUExpert(cfg.n_embd, cfg.n_ff) for _ in range(cfg.n_experts)
        )
        self.shared = nn.ModuleList(
            SwiGLUExpert(cfg.n_embd, cfg.n_ff)
            for _ in range(cfg.n_shared_experts)
        )
        # 选择偏置：不进 AdamW，只影响 top-k 比较
        self.register_buffer(
            "route_bias", torch.zeros(cfg.n_experts), persistent=True
        )
        self._last_loads = None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, n, d] → flat: [T, d]，T = B*n
        B, n, d = x.shape
        flat = x.reshape(B * n, d)
        scores = self.router(flat) * self.cfg.route_scale

        # 用 s+b 做选择；用原始 s 在 top-k 上取权重
        _, topi = torch.topk(
            scores + self.route_bias, self.cfg.n_experts_per_tok, dim=-1
        )
        gate_logits = torch.gather(scores, dim=-1, index=topi)
        gates = F.softmax(gate_logits, dim=-1)

        out = torch.zeros_like(flat)
        loads = torch.zeros(self.cfg.n_experts, device=x.device)
        for j in range(self.cfg.n_experts_per_tok):
            expert_ids = topi[:, j]
            weight = gates[:, j]
            for expert_id in expert_ids.unique().tolist():
                token_idx = (expert_ids == expert_id).nonzero(as_tuple=False).squeeze(1)
                piece = self.experts[expert_id](flat[token_idx])
                out[token_idx] = out[token_idx] + weight[token_idx].unsqueeze(1) * piece
                loads[expert_id] += token_idx.numel()

        for shared in self.shared:
            out = out + shared(flat)

        self._last_loads = loads.detach()
        return out.view(B, n, d)

    @torch.no_grad()
    def update_route_bias(self, lr: float = 1e-2) -> None:
        if self._last_loads is None:
            return
        loads = self._last_loads.float()
        self.route_bias += lr * torch.sign(loads.mean() - loads)
```

`scores` 保存原始路由分数。`topi` 保存每个 token 选中的 \(k\) 个专家编号，形状为 `[T,k]`；`gates` 保存对应混合权重。`topk` 用 `scores + route_bias` 决定编号，softmax 从原始 `scores` 取值，因此偏置只调节专家被选中的频率。

将第 8 章 Block 中的 FFN 替换为 `MoESwiGLU`：

```python
class ModernBlockMoE(nn.Module):
    def __init__(self, gpt_cfg, moe_cfg: MoEConfig):
        super().__init__()
        self.attn_norm = RMSNorm(gpt_cfg.n_embd, gpt_cfg.norm_eps)
        self.attn = GQAAttention(gpt_cfg)
        self.ffn_norm = RMSNorm(gpt_cfg.n_embd, gpt_cfg.norm_eps)
        self.ffn = MoESwiGLU(moe_cfg)

    def forward(self, x, past_kv=None, use_cache=False):
        attn_out, new_kv = self.attn(
            self.attn_norm(x), past_kv=past_kv, use_cache=use_cache
        )
        x = x + attn_out
        x = x + self.ffn(self.ffn_norm(x))
        return x, new_kv
```

`RMSNorm` 与 `GQAAttention` 沿用第 8 章。每次 `optimizer.step()` 之后，可以遍历所有 `MoESwiGLU` 并调用 `update_route_bias()`。`_last_loads` 是长度为 \(N\) 的负载直方图。

参数统计只计算 FFN 段：

```python
def count_moe_ffn(m: MoESwiGLU) -> tuple[int, int]:
    p_expert = sum(p.numel() for p in m.experts[0].parameters())
    n, k = m.cfg.n_experts, m.cfg.n_experts_per_tok
    n_shared = m.cfg.n_shared_experts
    p_router = sum(p.numel() for p in m.router.parameters())
    total = (n + n_shared) * p_expert + p_router
    active = (k + n_shared) * p_expert + p_router
    return total, active
```

路由器相对专家通常很小。\(N=8\)，\(k=2\)，\(n_{\text{shared}}=1\) 时，`total/active` 接近 \(9/3=3\)。加入公共注意力之后，整网的总参/激活比会低于 3。

## 9.7 训练与部署

参考代码使用 Python 循环，适合核对路由结果与参数量。实际训练先按专家编号重排 token，将发往同一专家的输入拼成矩阵，再用 grouped GEMM 执行多组专家计算。

专家分布在多张卡上时，token 按路由结果发送到持有对应专家的设备，计算完成后再返回原序列位置。这两次重排通常通过 all-to-all 完成。显存仍按总参数估：235B 总参的 bf16 权重约 470 GB；激活参数只描述一次前向实际经过多少权重。专家并行的通信量，负载偏斜与 grouped GEMM 效率共同决定实际吞吐。


---

## 核心问答

**Q1：专家会自动按主题分工吗？**
训练只提供语言模型损失和负载约束，没有主题标签。分工由路由与专家参数共同形成，可能对应语言，代码，词法类别，也可能对应难以直接命名的内部特征。

**Q2：选择偏置为何不进入混合权重？**
偏置调节专家被选中的频率；原始路由分数决定选中后各专家的混合比例。两组量分开后，负载控制不会直接改写层输出的权重。

**Q3：共享专家要不要算进激活参数？**
要。每个 token 都会跑共享专家，激活里应加 \(n_{\text{shared}} P_E\)。

**Q4：辅助损失和选择偏置可以一起用吗？**
可以。较弱的辅助损失可以处理局部负载，选择偏置再调节长期分布。具体组合取决于模型规模，专家并行布局与训练稳定性。

**Q5：大 batch 下的实际加速为何低于 \(k/N\) 的理论比例？**
大 batch 里不同 token 的路由往往覆盖绝大多数专家，权重读取接近稠密；省下的主要是乘加。服务场景要看专家侧能否聚成大块 GEMM，以及 all-to-all 是否被掩盖。
