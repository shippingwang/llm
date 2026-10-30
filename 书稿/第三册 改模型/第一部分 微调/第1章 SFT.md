# 第 1 章 SFT

SFT即监督微调

## 1.1 迁移学习

在开始介绍SFT之前我们先明确几个类似的概念

1. 迁移学习
2. 表征学习
3. 增量学习
4. 主动学习
5. SFT

首先看一下迁移学习，就是普通finetune做了什么，为什么SFT是一种finetune
    
1. **普通Finetune**（如ImageNet迁移学习）：
    - **数据**：通常使用**非结构化或弱标注数据**（如分类标签），例如将在ImageNet上预训练的ResNet模型直接应用于新的图像分类任务，仅需新类别的标签即可微调。
    - **目标**：主要是适配新任务的输出空间（如改变分类层），模型的核心能力（如特征提取）未发生本质变化。
    - **技术路径**：通过最小化预测结果与标签的差异（如交叉熵损失）更新模型参数，属于模型被动适应。
2. **SFT（监督微调）**：
    - **数据**：依赖**人工标注的高质量输入-输出对**，例如针对对话任务的指令-回答数据
    - **目标**：显式注入领域知识或人类偏好，例如让模型学会遵循特定格式（如代码生成中的缩进规范）或避免有害内容。
    - **技术路径**：不仅调整输出层，还可能对中间层进行深度优化，属于主动引导。

## 1.2 SFT

SFT 能做什么？

1. 激活模型的指令理解能力：预训练模型（如 GPT-3 的基础版）仅能做 “文本续写”，而 SFT 后，模型能理解 “写一封道歉信”“解释相对论” 等复杂指令，实现从 “被动续写” 到 “主动响应” 的转变。
2. 统一多任务生成范式：通过多样化指令数据，SFT 让模型用同一架构支持多任务（无需为每个任务单独设计模型）。例如，经 SFT 的 Llama 3 既能做翻译（“将中文翻译成法语”），也能做逻辑推理（“甲比乙大，乙比丙大，谁最大？”）。
3. 为后续优化打基础：SFT 是大模型 “对齐流程” 的第一步（SFT→RM→RLHF），其输出的模型（SFT Model）会作为后续强化学习（如 RLHF）的 “初始策略”。若 SFT 效果差（如指令理解错误），后续强化学习也难以弥补。
4. 降低模型 “幻觉” 与无意义输出：预训练模型可能生成与事实不符的内容（“幻觉”）或偏离指令的文本，而 SFT 通过高质量响应数据的约束，能显著减少这类问题（例如，训练模型在 “不知道答案” 时输出 “我不确定”，而非编造内容）。

这里我们假设已经有了一个底座模型，在它基础上进行微调让他拥有“行程助手”的能力

### 1.2.1  SFT数据


SFT 的训练数据是人工标注的**指令 - 回答样本对**，所有样本统一通过对话模板封装，单条样本被明确划分为两个区域：

- **prompt 区**：用户的问题，指令或上下文输入，作为模型生成回答的前提条件
- **response 区**：期望模型输出的标准答案，是训练的监督目标

以行程助手场景为例，单条样本的完整格式为：

```
<|user|>
五一想去杭州玩三天
<|assistant|>
Day1：西湖环湖线，清晨逛断桥，白堤，午后走苏堤，登雷峰塔，傍晚看湖滨音乐喷泉
Day2：灵隐寺祈福，下午逛龙井村，走九溪烟树，体验茶园春色
Day3：逛河坊街与南宋御街，感受老城烟火，午后准备返程
```

全部样本经分词后得到 token 序列，同时记录 prompt 与 response 的位置分界，用于后续损失计算。

### 1.2.2 SFT的loss

沿用自回归交叉熵损失，核心规则：**仅 response 区参与损失计算与梯度回传，prompt 区全部忽略**。
实现方式：构造标签张量时，将 prompt 对应的所有 token 位置替换为忽略标记（PyTorch 交叉熵默认忽略值为 - 100），仅保留 response 区的原始 token id。

以上述样本为例，简化的对应关系如下：

- 完整 token 序列（示意）：`[<|user|>, 五一, 想, 去, 杭州, 玩, 三天, <|assistant|>, Day1, ：, 西湖, ... , 返程]`
- 对应 labels 张量：`[-100, -100, -100, -100, -100, -100, -100, -100, Day1_id, ：_id, 西湖_id, ... , 返程_id]`

模型前向逐位置预测下一个 token，与 labels 计算交叉熵时，所有标记为 - 100 的 prompt 位置会被自动跳过，损失仅由助手回答的 token 贡献，再基于该损失反向传播更新全部参数。


## 1.6 LoRA

这里我们继续介绍PEFT中的Lora，即参数高效微调

全参数监督微调虽然效果上限最高，但显存开销大，容易引发灾难性遗忘，多业务场景权重管理成本高。为了解决这些问题，学界提出了参数高效微调（PEFT）系列方法，其中**LoRA（Low-Rank Adaptation，低秩适配）**是目前工业界最主流，工程落地最友好的方案。

LoRA 的核心假设是：大模型在适配下游任务时，权重的更新量本质上是低秩的—— 权重变化的有效信息可以被压缩到一个远小于原权重维度的低秩空间里，不需要更新整个权重矩阵。

对于模型某一层的原生权重矩阵 \(W \in \mathbb{R}^{d \times k}\)，全参数微调是直接修改整个 \(W\)，得到更新后的 \(W + \Delta W\)。
LoRA 不直接改动原权重，而是在旁边新增两个低秩矩阵 \(B \in \mathbb{R}^{d \times r}\) 和 \(A \in \mathbb{R}^{r \times k}\)，用二者的乘积来近似权重更新量 \(\Delta W\)：

\[
\Delta W = BA
\]

其中秩 \(r \ll \min(d, k)\)，通常取 4，8，16 等很小的数值。

前向计算时，输出由原权重和 LoRA 分支共同得到：

\[
h = Wx + \Delta W x = Wx + BAx
\]

训练过程中，原权重 \(W\) 完全冻结，不参与梯度更新；只训练 \(A\) 和 \(B\) 两个小矩阵。训练完成后，可以将 \(BA\) 合并回原权重 \(W\)，推理时和全参数微调的模型结构完全一致，不会引入额外推理延迟。


### 作用位置

LoRA 通常插入在 Transformer 的自注意力投影层中，最常见的是查询（Q），值（V）投影矩阵，也可以扩展到键（K），输出（O）投影，甚至前馈网络（FFN）层。
选择注意力投影层的原因：这部分权重承载了模型的语义关联与指令跟随能力，是微调时最需要适配的部分；同时参数量占比高，用低秩近似带来的显存收益最明显。

### rank

秩 r 控制着 LoRA 的参数量与表达能力：

- r 越小，参数量越少，训练越快，但可表达的任务信息有限；
- r 越大，表达能力越强，但参数量和显存开销随之上升，且当 r 超过一定阈值后，效果不会持续提升。
工业实践中，多数指令微调场景 \(r=8\) 或 \(r=16\) 就足以达到接近全参数微调的效果。

### 3初始化策略

- 矩阵 A 采用小方差高斯分布随机初始化；
- 矩阵 B 初始化为全零。
这样设计保证了训练启动时

\[
\Delta W = BA = 0
\]

模型的初始输出和原生基座完全一致，不会因为新增模块扰动预训练权重，训练过程更稳定。

### 推理开销

这是 LoRA 相比 Adapter 等其他 PEFT 方法的核心优势：训练完成后，可以直接将 BA 合并到原权重 W 中，得到和全参数微调结构完全一致的模型，推理时没有任何额外计算层与延迟。也可以在推理时动态加载 / 切换不同的 LoRA 权重，实现一套基座适配多个业务场景。


## 1.7 LoRA 微调

1. **加载基座并冻结权重**
加载预训练基座模型与分词器，将基座所有参数设置为冻结状态，不计算梯度，不参与更新。
2. **注入 LoRA 模块**
在指定的注意力投影层（如 Q，V 层）旁，添加对应维度的 A，B 低秩矩阵，这部分是唯一可训练的参数。
3. **数据与损失计算**
沿用和全参数 SFT 完全相同的数据格式：按对话模板封装指令 - 回答对，对 prompt 区域设置损失掩码（标签置为 - 100），仅在 response 区域计算自回归交叉熵损失。数据清洗，分批规则也与全参数 SFT 一致。
4. **训练循环**
前向传播时，原权重与 LoRA 分支共同计算输出；反向传播时，梯度仅回传到 LoRA 的 A，B 矩阵，仅更新这部分参数。优化器只需维护少量 LoRA 参数的状态，显存开销远低于全参数微调。
5. **保存与部署**
训练完成后，默认只保存 LoRA 的 A，B 权重文件，体积通常只有几十 MB，远小于完整基座。部署时有两种选择：

- 静态合并：将 LoRA 权重合并到基座中，导出完整模型，推理无额外开销；

\[
W_{\mathrm{merged}} = W + \Delta W_1 + \Delta W_2 + \cdots
\]

- 动态加载：推理时按需加载不同 LoRA 权重，一套基座支撑多个业务角色。


## 1.8 LoRA 工程

这里我们直接看一下LoRA的工程代码，对于日常以微调为主的大模型算法工程师来说应该十分熟悉



### 训练

```python
import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

# ========== 1. 加载基座并冻结权重 ==========
model_name = "Qwen/Qwen2-7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

# 加载基座模型，默认冻结全部参数；开启4bit量化进一步降低显存
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    load_in_4bit=True  # 可选：4bit量化，7B模型单消费级卡即可训练
)

# ========== 2. 注入 LoRA 模块 ==========
lora_config = LoraConfig(
    r=8,                      # 低秩秩值，对应原理中的秩 r
    lora_alpha=16,            # 输出缩放系数
    target_modules=["q_proj", "v_proj"],  # 作用在注意力Q，V投影层
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# 给基座挂载LoRA，仅LoRA参数可训练，基座全程冻结
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()  # 可打印可训练参数量占比，通常 < 0.1%

# ========== 3. 构造数据集与损失掩码规则 ==========
# 示例：行程助手SFT数据，格式与前文完全一致
data = [
    {
        "instruction": "五一想去杭州玩三天",
        "output": "Day1：西湖环湖线，清晨逛断桥，白堤，午后走苏堤，登雷峰塔，傍晚看湖滨音乐喷泉\nDay2：灵隐寺祈福，下午逛龙井村，走九溪烟树，体验茶园春色\nDay3：逛河坊街与南宋御街，感受老城烟火，午后准备返程"
    },
    {
        "instruction": "元旦去乌兹别克斯坦撒马尔罕3天，怕冷，喜欢古迹",
        "output": "Day1：雷吉斯坦广场，夏伊辛达陵墓，傍晚看夕阳；户外单次停留不超过30分钟\nDay2：古尔埃米尔陵墓，兀鲁伯天文台，了解帖木儿王朝历史\nDay3：布哈拉古城半日游，午后返程"
    }
]
dataset = Dataset.from_list(data)

# 对话模板格式化函数
def format_prompt(sample):
    return f"<|user|>\n{sample['instruction']}\n<|assistant|>\n{sample['output']}"

# 损失掩码规则：只计算 <|assistant|> 之后的回答部分损失
# SFTTrainer 通过 response_template 自动实现 prompt 部分标签置 -100

# ========== 4. 配置训练参数并启动训练循环 ==========
training_args = TrainingArguments(
    output_dir="./lora_travel_assistant",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    num_train_epochs=2,
    logging_steps=10,
    save_strategy="epoch",
    bf16=True,
    optim="paged_adamw_8bit"
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=training_args,
    tokenizer=tokenizer,
    formatting_func=format_prompt,
    response_template="<|assistant|>\n",  # 核心：该标记之后的内容才计算损失
    max_seq_length=512
)

# 启动训练：前向走双分支，反向仅更新LoRA参数
trainer.train()

# ========== 5. 保存 LoRA 权重 ==========
# 仅保存A，B低秩矩阵，体积几十MB，不保存完整基座
model.save_pretrained("./lora_travel_assistant_final")
tokenizer.save_pretrained("./lora_travel_assistant_final")
```


- `response_template="<|assistant|>\n"` 自动实现了前文所述的损失掩码：标记之前的用户指令部分标签置为 -100，不参与损失计算，仅回答部分回传梯度。
- 训练全程基座权重冻结，仅 LoRA 的 A，B 矩阵更新，优化器只需维护少量参数状态，显存开销远低于全参数 SFT。

---

#### 推理
对应动态加载部署方式，一套基座可切换多个业务 LoRA。

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# 加载原生基座
base_model_name = "Qwen/Qwen2-7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(base_model_name)
model = AutoModelForCausalLM.from_pretrained(
    base_model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

# 加载训练好的LoRA权重，不修改基座本身
model = PeftModel.from_pretrained(model, "./lora_travel_assistant_final")

# 推理生成
prompt = "<|user|>\n国庆去成都玩3天，想吃火锅\n<|assistant|>\n"
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

outputs = model.generate(
    **inputs,
    max_new_tokens=200,
    temperature=0.7,
    do_sample=True
)

print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

---

#### 权重合并与静态推理
对应静态合并部署方式，合并后与全参数微调模型结构一致，推理无额外开销。

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

base_model_name = "Qwen/Qwen2-7B-Instruct"
lora_path = "./lora_travel_assistant_final"

# 加载基座 + LoRA
tokenizer = AutoTokenizer.from_pretrained(base_model_name)
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_name,
    torch_dtype=torch.bfloat16,
    device_map="cpu"  # 合并建议在CPU执行，避免显存不足
)
model = PeftModel.from_pretrained(base_model, lora_path)

# 合并权重：将 BA 乘积并入原权重 W
merged_model = model.merge_and_unload()

# 保存合并后的完整模型，可直接用于推理部署
merged_model.save_pretrained("./merged_travel_assistant")
tokenizer.save_pretrained("./merged_travel_assistant")
```

合并后的模型使用方式和原生基座完全一致，无需额外加载 LoRA，推理速度无损失。