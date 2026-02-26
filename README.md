# SWE-CI: Evaluating Agent Capabilities in Maintaining Codebases via Continuous Integration

<p align="center">
  [简体中文] | English
</p>

🔗 HuggingFace 链接: https://huggingface.co/datasets/SWE-CI/SWE-CI

🔗 论文链接: 即将发布...


## Leader Board

|Model| CLI Agent | M1 | M2 | M3 | M4 | M5 |  Overall $\uparrow$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude-opus-4-6 | iFlow | 0.9607 | 0.9817 | 0.9152 | 0.9200 | 0.7600 | 0.9075 |
| GLM-5 | iFlow | 0.8544 | 0.9199 | 0.6756 | 0.6400 | 0.3600 | 0.6900 |
| Qwen3.5-plus | iFlow | 0.7996 | 0.8678 | 0.6177 | 0.6200 | 0.2000 |  0.6210 |
| MiniMax-M2.5 | iFlow | 0.7952 | 0.8433 | 0.6416 | 0.5200 | 0.2000 |  0.6000 |
| Kimi-K2.5 | iFlow | 0.7351 | 0.7276 | 0.6978 | 0.3100 | 0.3700 |  0.5681 |  
| DeepSeek-V3.2 | iFlow | 0.7427 | 0.7959 | 0.4325 | 0.4400 | 0.2000 |  0.5222 | 
| GLM-4.7 | iFlow | 0.7402 | 0.7786 | 0.5395 | 0.4100 | 0.1400 | 0.5217 |
| GPT-5.2 | iFlow | 0.7206 | 0.6840 | 0.5789 | 0.2900 | 0.2300 |  0.5007 |
| GPT-5.3-codex | iFlow | 0.6343 | 0.4851 | 0.7441 | 0.1300 | 0.3700 | 0.4727 |
| Kimi-K2-Thinking | iFlow | 0.6941 | 0.7364 | 0.3628 | 0.3500 | 0.1500 | 0.4587 |
| Kimi-K2-Instruct-0905 | iFlow | 0.6907 | 0.7467 | 0.3714 | 0.3600 | 0.1200 | 0.4578 |
| MiniMax-M2.1 | iFlow | 0.6870 | 0.6697 | 0.5377 | 0.2300 | 0.1500 | 0.4549 |
| GLM-4.6 | iFlow |  0.6885 | 0.6928 | 0.4274 | 0.3000 | 0.1400 | 0.4497 |
| QWen3-Max-2026-01-23 | iFlow | 0.6594 | 0.6917 | 0.3826 | 0.3000 | 0.0900 | 0.4248 |
| QWen3-Max-2025-09-23 | iFlow | 0.6564 | 0.6601 | 0.3737 | 0.2300 | 0.0700 | 0.3980 |
| Qwen3-coder-plus | iFlow | 0.6185 | 0.5818 | 0.3823 | 0.2100 | 0.1000 | 0.3785 |

See the definition of the metric [here](docs/metrics.md).


## 快速开始

### 🌍 适用性
仓库目前仅支持 Linux 操作系统 和 iFlow CLI。未来将逐步支持Windows 操作系统，CaludeCode CLI 和 OpenCode CLI。
### 💰 参考开销
在以下测试环境下，在全量数据集 (full.csv) 上运行本项目约需 **48 小时**：
+ 硬件配置：32-core CPU, 64 GB RAM, 约 1 GB/s 磁盘读写速度
+ 并发设置：16 并发
+ API Key：至少 16 个并发请求的 LLM API Key。

### 🚀 安装

**步骤1：** 本仓库基于 Docker 开发，在首次运行本仓库之前请先使用以下命令确保 Docker 正常运行。
```bash
docker run hello-world
```
理想情况下，您将会在输出中看到 “Hello form Docker!” 的字样。 您可以在 [这里](https://www.docker.com/get-started/) 查阅Docker的安装方式。

**步骤2:** 从 Github 下载并安装该项目。默认使用 [Anaconda](https://www.anaconda.com/download) / [Miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install) / [Miniforge](https://github.com/conda-forge/miniforge) 管理Python环境。
```bash
git clone https://github.com/Loong-Chan/SWE-CI.git
cd SWE-CI

conda create --name sweci python=3.11 -y
conda activate sweci
pip install -r requirements.txt
```

### 🏃 运行

**从 Hugging Face 下载数据集：** 首次运行试验需要先从 Hugging Face 上下载数据。全量数据集（full.csv）大约需要 52.8Gb 存储空间。
```bash
# （推荐）使用默认参数下载
PYTHONPATH=src python -m swe_ci.download

# （个性化）使用自定义参数下载
# --splitting: 可选，数据集划分，默认值 "full"
# --hf_token: 可选，用于加速加载，默认值 "none"
PYTHONPATH=src python -m swe_ci.download \
    --splitting <SPLITTING> \
    --hf_token <HF_TOKEN>
```

**运行实验**：
+ 在默认情况下，您可以完全使用命令行传递参数。其中，`--api_key` / `--base_url` / `--model_name` 兼容OpenAI的接口协议。您也可以通过将 `--iflow.auth_type` 设置为 `iflow`以使用 iFlow 接口协议，详细信息请查阅 [iFlow 官方文档](https://platform.iflow.cn/docs)。
+ 本实验包含 *任务初始化* 和 *代码演进* 两个阶段。任务初始化大约耗时30分钟（并发数=16时）。当系统资源比较紧张时，个别任务可能会初始化超时。此时请适当降低对Docker容器的资源限制或减少并发数并重新执行命令。只有当所有任务完成初始化之后才会进入代码演化阶段（约48小时）。
```bash
# --experiment_name 必填，用于唯一标识该实验的字符串，通过复用 experiment_name 可以实现断点续跑
# --splitting 可选，默认值 "full"，数据集划分，应与下载时使用的参数保持一致
# --api_key / --base_url / --model_name 必填
PYTHONPATH=src nohup python -u -m swe_ci.evaluate \
    --experiment_name <EXPERIMENT_NAME> \
    --splitting <SPLITTING> \
    --api_key <API_KEY> \
    --base_url <BASE_URL> \
    --model_name <MODEL_NAME> \
    > temp.log 2>&1 &
```
+ 更方便的做法是，您可以直接修改项目中的 config.toml 文件，并为其中的任意参数重新设置默认参数。以实现更精细的实验设置和避免在命令行重复输入参数。
```bash
# 假设所有必填项都已经在config.toml中被设置
PYTHONPATH=src nohup python -u -m swe_ci.evaluate > temp.log 2>&1 &
```
+ 如果您有在多组不同的设置下运行实验的需求，我们建议您为每一组实验单独创建一份配置文件，并使用 `--config_file` 参数指定您的个性化配置文件。
```bash
# 假设创建一份新的配置文件 my_config_1.toml（需与config.toml 位于同一目录下，且配置项与config.toml相同），并已在其中指定所有必填项。
PYTHONPATH=src nohup python -u -m swe_ci.evaluate \
    --config_file my_config_1.toml \
    > temp.log 2>&1 &
```
⚠️ 由于实验运行时间较长（16并发下需要约48小时），我们建议您在执行上述命令后记录下命令的PID以便在必要时候任何必要时候提前杀死进程。

⚠️ 您可以根据自身的资源情况在 config.toml 中调整并发数和 Docker 容器的资源使用限制，包括CPU、内存和IO。

⚠️ 由于某些意外情况（如：API Key的并发数超过限制，或Agent的不恰当的修改使得代码运行超时）导致个别任务执行失败属于正常现象。大多数情况下可以通过重新运行试验解决。

### 📄 查看试验结果
您可以通过指定 ` --experiment_name` 和 `--splitting` 参数来查看试验结果。
```bash
PYTHONPATH=src python -m swe_ci.summarize \
    --experiment_name <EXPERIMENT_NAME> \
    --splitting <SPLITTING>
```

