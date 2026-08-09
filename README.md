# 🩺 GPUNodeDiag

[![CI](https://github.com/aminmsalimi/gpu-node-diag/actions/workflows/ci.yml/badge.svg)](https://github.com/aminmsalimi/gpu-node-diag/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-Apache--2.0-green)

**GPUNodeDiag** is a Linux-focused NVIDIA GPU diagnostics and troubleshooting CLI.

Instead of only showing raw GPU metrics, `gdiag` checks the GPU stack step by step and turns the results into useful findings, severity levels, evidence, and recommended actions.

## ⚡ Quick install

```bash
curl -fsSL https://raw.githubusercontent.com/aminmsalimi/gpu-node-diag/main/install.sh | bash
```

Then run:

```bash
gdiag
```

## 🔍 What it checks

- GPU discovery, utilization, memory, temperature and power
- PCIe link health
- ECC errors and NVIDIA Xid events
- NVLink and GPU fabric
- Fabric Manager
- NVIDIA DCGM
- NVIDIA driver and CUDA stack
- NVIDIA Container Toolkit and container runtimes
- Kubernetes GPU resources and NVIDIA Device Plugin

## 🛠 Main commands

```bash
gdiag
gdiag --gpu 0
gdiag --deep
gdiag --json

gdiag watch
gdiag report
gdiag stack
gdiag container
gdiag k8s
```

### Live monitoring

```bash
gdiag watch
```

### HTML diagnostic report

```bash
gdiag report -o gpu-report.html
```

### Driver / CUDA diagnostics

```bash
gdiag stack
```

### Container diagnostics

```bash
gdiag container
```

### Kubernetes GPU diagnostics

```bash
gdiag k8s
```

## 📦 Manual installation

```bash
git clone https://github.com/aminmsalimi/gpu-node-diag.git
cd gpu-node-diag

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

## 🛡 Safety

Normal GPUNodeDiag checks are designed to be read-only.

`gdiag --deep` explicitly enables deeper NVIDIA DCGM diagnostics and may exercise the GPUs.

## 🐧 Platform

GPUNodeDiag is primarily designed for **Linux NVIDIA GPU infrastructure**.

Some functionality also works on Windows for development and basic inspection.

## 📜 License

Apache License 2.0.
