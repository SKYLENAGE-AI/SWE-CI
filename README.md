English | [中文](README_zh.md)

# SWE-CI: Evaluating Agent Capabilities in Maintaining Codebases via Continuous Integration

🔗 HuggingFace: https://huggingface.co/datasets/skylenage/SWE-CI

🔗 Paper: https://arxiv.org/pdf/2603.03823

💡 We are developing [Otter](https://github.com/GalenChen320/Otter/tree/main), an agent evaluation framework based on multi-turn environment feedback. SWE-CI will be more comprehensively supported within Otter in the near future.

## Introduction
![](docs/1.png)

### 🏆 What is SWE-CI?

Code maintainability is crucial throughout the software lifecycle. SWE-CI is the first benchmark specifically designed to evaluate *the ability of AI agents to maintain repositories*. The core insight behind SWE-CI is that **good maintenance not only ensures the functional correctness of the current code, but also minimizes the difficulty of keeping the code functionally correct in the future.**

SWE-CI curates 100 high-quality pairs of code commit versions from GitHub. Each pair consists of a base commit and a reference commit, drawn from different points in time within the same repository. SWE-CI requires AI agents to start from the base commit and work toward passing all tests from the reference commit. By quantifying the degree to which functional correctness is sustained across a code evolution sequence, SWE-CI effectively measures an AI agent's ability to maintain code.

SWE-CI introduces a unique **dual-agent collaborative workflow** that simulates the continuous integration loop (CI-loop) used by real-world professional software teams during code maintenance:

- **Architect Agent**: Responsible for analyzing test information provided by the automated testing system. Through failure attribution, code localization, and requirement design, it produces professional, high-level requirement documents in natural language, which are then handed off to the programmer for implementation.

- **Programmer Agent**: Upon receiving the requirement document, the programmer agent translates the requirements into concrete code behavior specifications, plans the maintenance strategy, and ultimately implements the code changes.

By repeatedly executing the closed-loop process of **"Run Tests → Define Requirements → Modify Code"**, SWE-CI effectively simulates real-world software development iteration cycles, providing a new platform for systematically measuring the comprehensive ability of agents to **maintain codebases over the long term**.

### 🏆 Why SWE-CI?

Compared to previous benchmarks, SWE-CI introduces **three fundamental shifts**:

#### 1️⃣ From Snapshot Fixes to Evolutionary Tracking

Most mainstream benchmarks follow the **"Issue → PR"** single-point fix paradigm: given a bug report at a specific moment, the model must complete the fix in one shot. However, real-world software engineering tasks are almost never one-and-done. SWE-CI moves beyond fixing individual bugs and instead focuses on the **evolutionary trajectory between two commit versions** (from the current commit to the target commit). It faithfully reproduces the dynamic process of a codebase continuously growing, refactoring, and evolving over time.

#### 2️⃣ From Static Requirement Descriptions to Dynamic Requirement Generation

SWE-CI does not rely on manually pre-written issue descriptions. Instead, it uses the **"Test Gap"** between the current code and the reference code as the core driver for generating requirement documents. In real-world software engineering, requirements are often highly dependent on the current state of the code and are difficult to predict in advance. By incorporating automated testing from the continuous integration process, SWE-CI achieves real-time detection of functional deficiencies and automated requirement generation.

#### 3️⃣ From Evaluating Correct Code to Evaluating Maintainable Code

SWE-CI goes beyond whether an agent can correctly implement requirements in a single attempt — it also examines whether that correctness can be sustained over time. By continuously tracking the functional correctness of code change sequences, SWE-CI objectively quantifies the otherwise vague concept of "maintainability," offering new insights for building more capable agent systems.


## Leaderboard

![](docs/result.png)


In SWE-CI, we use Average Normalized Change (ANC) to measure a model's ability to maintain code. We define the following notation:

*   $p_i^{(j)}$: The number of unit tests passed by the code at iteration $i$ for task $j$. Here, $p_0^{(j)}$ denotes the number of unit tests passed by the initial code before any iterations for task $j$.
*   $p_{\ast}^{(j)}$: The total number of unit tests that need to be passed for task $j$, equivalent to the number of unit tests passed by the reference code (ground truth).
*   $N$: The maximum number of iterations.
*   $M$: The total number of tasks in the dataset.

We first define Normalized Change (NC) as the relative improvement (including both positive and negative changes) in a given iteration compared to the baseline:

$$
a_i^{(j)}=\begin{cases}
\dfrac{p_i^{(j)}-p_0^{(j)}}{p_\ast^{(j)}-p_0^{(j)}}, & \text{if}\ p_i^{(j)} \geq p_0^{(j)}\\
\dfrac{p_i^{(j)}-p_0^{(j)}}{p_0^{(j)}}, & \text{if}\ p_i^{(j)} < p_0^{(j)}
\end{cases}
$$

The Average Normalized Change is then defined as:

$$
{\rm ANC} =\frac{1}{MN}\sum_{j=1}^M\sum_{i=1}^N a_i^{(j)}
$$

This metric comprehensively captures the changes in functional correctness across the entire code maintenance cycle, serving as a reliable measure of an agent's code maintenance capability.


## Quick Start

### 🌍 Compatibility
This repository is designed to run on Linux with [iFlow CLI](https://arxiv.org/abs/2512.24873).

### 💰 Estimated Cost
Under the following test environment, running the full dataset (full.csv) takes approximately **48 hours**:
+ Hardware: 32-core CPU, 64 GB RAM, ~1 GB/s disk I/O speed
+ Concurrency: 16 concurrent workers
+ API Key: An LLM API key that supports at least 16 concurrent requests.

### 🚀 Installation

**Step 1:** This repository is built on Docker. Before running it for the first time, make sure Docker is working properly with the following command:
```bash
docker run hello-world
```
Ideally, you should see "Hello from Docker!" in the output. You can find Docker installation instructions [here](https://www.docker.com/get-started/).

**Step 2:** Clone and install the project from GitHub. We recommend using [Anaconda](https://www.anaconda.com/download) / [Miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install) / [Miniforge](https://github.com/conda-forge/miniforge) to manage Python environments.
```bash
git clone https://github.com/Loong-Chan/SWE-CI.git
cd SWE-CI

conda create --name sweci python=3.11 -y
conda activate sweci
pip install -r requirements.txt
```

### 🏃 Running

**Download the dataset from Hugging Face:** The dataset must be downloaded from Hugging Face before running experiments for the first time. The full dataset (full.csv) requires approximately 52.8 GB of storage.
```bash
# (Recommended) Download with default parameters
PYTHONPATH=src python -m swe_ci.download

# (Custom) Download with custom parameters
# --splitting: Optional, dataset split, default "full"
# --hf_token: Optional, used to speed up loading, default "none"
PYTHONPATH=src python -m swe_ci.download \
    --splitting <SPLITTING> \
    --hf_token <HF_TOKEN>
```

**Run experiments:**
+ By default, you can pass all parameters via the command line. The `--api_key` / `--base_url` / `--model_name` parameters are compatible with the OpenAI API protocol. You can also set `--iflow.auth_type` to `iflow` to use the iFlow API protocol. For details, please refer to the [iFlow official documentation](https://platform.iflow.cn/docs).
+ The experiment consists of two phases: *task initialization* and *code evolution*. Task initialization takes approximately 30 minutes (with 16 concurrent workers). When system resources are limited, some tasks may time out during initialization. In that case, consider lowering the Docker container resource limits or reducing concurrency, and re-run the command. The code evolution phase (~48 hours) begins only after all tasks have been initialized.
```bash
# --experiment_name Required, a unique string identifying the experiment; reusing the same name enables resuming from checkpoints
# --splitting Optional, default "full", dataset split; should match the value used during download
# --api_key / --base_url / --model_name Required
PYTHONPATH=src nohup python -u -m swe_ci.evaluate \
    --experiment_name <EXPERIMENT_NAME> \
    --splitting <SPLITTING> \
    --api_key <API_KEY> \
    --base_url <BASE_URL> \
    --model_name <MODEL_NAME> \
    > temp.log 2>&1 &
```
+ A more convenient approach is to edit the `config.toml` file in the project and set default values for any parameters. This allows for finer-grained experiment configuration and avoids repeatedly typing parameters on the command line.
```bash
# Assuming all required fields have been set in config.toml
PYTHONPATH=src nohup python -u -m swe_ci.evaluate > temp.log 2>&1 &
```
+ If you need to run experiments under multiple different configurations, we recommend creating a separate configuration file for each setup and specifying it with the `--config_file` parameter.
```bash
# Assuming a new configuration file my_config_1.toml has been created (in the same directory as config.toml, with the same configuration fields) and all required fields have been set.
PYTHONPATH=src nohup python -u -m swe_ci.evaluate \
    --config_file my_config_1.toml \
    > temp.log 2>&1 &
```
⚠️ Since experiments take a long time to run (~48 hours with 16 concurrent workers), we recommend noting the PID of the command after execution so you can terminate the process early if needed.

⚠️ You can adjust the concurrency level and Docker container resource limits (CPU, memory, and I/O) in `config.toml` based on your available resources.

⚠️ It is normal for individual tasks to fail due to unexpected situations (e.g., API key concurrency limits exceeded, or inappropriate agent modifications causing code execution timeouts). In most cases, this can be resolved by re-running the experiment.

### 📄 Viewing Experiment Results
You can view experiment results by specifying the `--experiment_name` and `--splitting` parameters:
```bash
PYTHONPATH=src python -m swe_ci.summarize \
    --experiment_name <EXPERIMENT_NAME> \
    --splitting <SPLITTING>
```

## 📖 Citation

If you find **SWE-CI** helpful for your research, please consider citing:

```bibtex
@article{chen2026swe,
  title={SWE-CI: Evaluating Agent Capabilities in Maintaining Codebases via Continuous Integration},
  author={Chen, Jialong and Xu, Xander and Wei, Hu and Chen, Chuan and Zhao, Bing},
  journal={arXiv preprint arXiv:2603.03823},
  year={2026}
}
