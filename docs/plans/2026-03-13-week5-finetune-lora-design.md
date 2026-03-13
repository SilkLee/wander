# Week 5 Design — Fine-tuning Classifier (LoRA on Qwen2.5-7B)

**Date**: 2026-03-13  \
**Scope**: Week 5 (Fine-tuning classifier)

## 1) Goal
Build a **LoRA fine‑tuned classifier** for PR risk (low/medium/high) on **Qwen2.5‑7B**, with a reusable training API and evaluation pipeline. The LoRA adapter is loaded by model‑service for inference; finetune runs are isolated in a dedicated service.

## 2) Non‑Goals
- No end‑user UI changes.
- No replacement of the primary generative model for other workflows.
- No fully automated data labeling at scale without human anchor checks.

## 3) Approach Summary
Use **HuggingFace Transformers + PEFT + TRL** in a new `services/finetune` service. Training is driven via API, produces LoRA adapters + metrics, and supports repeated iterations. Inference uses LoRA adapters loaded by model‑service and returns risk labels for workflow integration.

## 4) Architecture & Components
**Training Service (new)**
- `services/finetune` – isolated training API, dataset preparation, evaluation.
- `POST /train` → start a training run.
- `POST /evaluate` → evaluate a given run.

**Artifacts**
- `artifacts/finetune/<run_id>/adapter_config.json`
- `artifacts/finetune/<run_id>/adapter_model.safetensors`
- `artifacts/finetune/<run_id>/metrics.json`

**Inference**
- `model-service` loads LoRA adapter for classifier inference.
- `agent-orchestrator` calls classifier endpoint for PR risk labels.

## 5) Data Flow
1) **Data Preparation**
   - Inputs from PR risk workflow outputs + small set of human‑validated labels.
   - Stored as JSONL with fields:
     - `input`: diff/context/summary
     - `label`: `low|medium|high`
     - `source`: `auto|human`

2) **Training**
   - Training API starts a run with configurable LoRA hyperparameters.
   - Outputs LoRA adapter and metrics.

3) **Evaluation**
   - Metrics: macro‑F1 + high‑risk recall priority.
   - Reports stored alongside run artifacts.

## 6) Integration & Deployment
- `finetune` is a **GPU‑only** training service.
- `model-service` loads LoRA for risk classification only.
- `agent-orchestrator` consumes classifier output as the risk signal for PR workflows.

## 7) Testing Strategy
- Unit tests: dataset preprocessing, label mapping, config validation.
- Integration tests: train → artifacts → load in model‑service.
- Offline eval: compare to baseline (previous workflow outputs).

## 8) Success Criteria
- LoRA classifier achieves **high‑risk recall improvement** vs baseline.
- Training API supports repeatable runs with tracked artifacts.
- model‑service successfully loads LoRA adapter for inference.
