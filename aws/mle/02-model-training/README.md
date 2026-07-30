# Lab 02 — Model Training (Domain 2: ML Model Development)

## Theory

SageMaker training jobs package model code, dependencies, data channels, and compute into reproducible runs. Instance type selection affects throughput/cost directly (CPU for smaller tabular baselines, GPU for deep learning workloads). **Spot training** can reduce cost significantly by using spare EC2 capacity, but jobs must tolerate interruptions and rely on checkpointing or sufficient `max_wait` time. **Distributed training** (especially data parallel) splits batches across workers to reduce wall-clock time for larger datasets and models.

For implementation style, **script mode** lets you bring custom training code (PyTorch/Scikit-learn/XGBoost scripts) while SageMaker manages infrastructure orchestration. **Built-in algorithms** are managed containers with predefined training logic (for example, XGBoost or Linear Learner), usually faster to start when your use case matches built-in assumptions. The trade-off is flexibility (script mode) versus speed of setup and operational simplicity (built-in).

Core training elements are tightly coupled: **epoch** (full pass over data), **batch size** (samples per gradient step), **steps** (optimizer updates), and **learning rate** (update magnitude). Regularization controls overfitting by constraining model complexity: **L1** encourages sparsity, **L2/weight decay** penalizes large weights, and **dropout** randomly drops activations during training to improve generalization.

Hyperparameter tuning strategies differ by search efficiency. **Grid search** is exhaustive but expensive, **random search** is often stronger than naive grids in high-dimensional spaces, and **Bayesian optimization** (used by SageMaker AMT) models prior results to choose the next most promising trial, often best for limited tuning budgets.

SageMaker **Model Registry** organizes models into **model package groups** and **versioned model packages**, each with an **approval status** (for example, PendingManualApproval → Approved/Rejected) to enforce governance before deployment. This supports auditable promotion workflows and separation between experimentation and production release.

For performance improvements beyond single-model baselines, **ensembling** combines learners (e.g., **boosting** or **stacking**) to reduce bias/variance trade-offs. Model size/latency can be reduced with **pruning** (remove low-importance parameters), **quantization** (lower precision representations), and **mixed precision** training/inference for better throughput and memory efficiency.

## Key Terms for Self-Study

- `SageMaker script mode`
- `SageMaker Estimator`
- `SageMaker Automatic Model Tuning (AMT)`
- `Bayesian optimization`
- `SageMaker Model Registry`
- `model approval workflow`
- `XGBoost built-in algorithm`
- `Linear Learner`
- `early stopping`
- `Spot training instances`
- `distributed training (data parallel)`
- `SageMaker Debugger`
- `confusion matrix`
- `F1 score`
- `precision recall tradeoff`
- `AUC ROC`
- `RMSE`

## Interview Talking Points

"I trained a PyTorch fraud detection model on SageMaker using script mode, compared it against XGBoost built-in, ran Bayesian HPO to find optimal hyperparameters, and versioned models in Model Registry with an approval workflow"

## Exam Tips

Domain 2 is 26%. Know when to use built-in algos vs script mode vs JumpStart. Know AMT strategies (Bayesian > random for small budgets). Know Model Registry approval workflow. Know regularization techniques by name and effect.

## References

- Karpathy "Zero to Hero" (YouTube)
- *Hands-On ML* Ch.10-11
- StatQuest "Regularization" + "XGBoost" videos
- AWS SageMaker Examples GitHub repo
