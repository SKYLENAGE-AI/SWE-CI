



## Notation

*   $p_i^{(j)}$: The number of unit tests passed by the code at the $i$-th iteration in the $j$-th task. Here, $p_0^{(j)}$ represents the number of unit tests passed by the initial code of task $j$ before the iteration process begins.
*   $p_{\ast}^{(j)}$: The total number of unit tests required to be passed in the $j$-th task, which is equivalent to the number of unit tests passed by the ground truth code.
*   $N$: The maximum number of iterations.
*   $M$: The total number of tasks in the dataset.

## Metrics

*   **Metric 1**: M1 measures the **overall consistency and average quality** of the process across all iterations and tasks, relative to the baseline and the target.

$$
a_i^{(j)}=\left\{
\begin{aligned}
& \frac{p_i^{(j)}-p_0^{(j)}}{p_\ast^{(j)}-p_0^{(j)}}, & {\rm if}\,\,p_i^{(j)} \geq p_0^{(j)}\\
& \frac{p_i^{(j)}-p_0^{(j)}}{p_0^{(j)}}, & {\rm if}\,\,p_i^{(j)} < p_0^{(j)}
\end{aligned}
\right.
$$

$$
{\rm M1} = \frac{1}{2}+\frac{1}{2MN}\sum_{j=1}^M\sum_{i=1}^N a_i^{(j)}
$$


*   **Metric 2**: M2 measures the **best-case performance** or the "ceiling" reached by the system.

$$
{\rm M2} =\frac{1}{M}\sum_{j=1}^M \frac{\max_{0 \leq i \leq N}p_i^{(j)}-p_0^{(j)}}{p_\ast^{(j)}-p_0^{(j)}}
$$

*   **Metric 3**: M3 measures the **worst-case performance** or the "floor," indicating the system's reliability and resistance to failure.

$$
{\rm M3} =\frac{1}{M}\sum_{j=1}^M \frac{\min_{0 \leq i \leq N}p_i^{(j)}}{p_0^{(j)}}
$$

*   **Metric 4**: M4 measures the **effectiveness** or the probability of reaching the ideal target.

$$
{\rm M4} = \frac{1}{M} \sum_{j=1}^{M} \mathbf{1}(\max_{0 \leq i \leq N}p_i^{(j)} = p_\ast^{(j)})
$$

*   **Metric 5**: M5 measures the **stability and progressiveness** of the process, specifically whether the performance improves or stays stable without regressing.

$$
{\rm M5} = \frac{1}{M} \sum_{j=1}^{M}\mathbf{1}(\forall i \in [1,N]: p_{i-1}^{(j)} \leq p_i^{(j)})
$$

*   **Overall**: M represents a holistic evaluation that balances average quality, peak potential, robustness, success rate, and stability.

$$
M = 0.2\,{\rm M1} + 0.2\,{\rm M2} + 0.2\,{\rm M3} + 0.2\,{\rm M4} + 0.2\,{\rm M5}
$$
