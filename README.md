# 🩺 GPUNodeDiag

[![CI](https://github.com/aminmsalimi/gpu-node-diag/actions/workflows/ci.yml/badge.svg)](https://github.com/aminmsalimi/gpu-node-diag"
Repository = "https://github.com/aminmsalimi/gpu-node-diag"
Issues = "https://github.com/aminmsalimi/gpu-node-diag/issues"

[project.scripts]
gdiag = "gpunodediag.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "build>=1.2"
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
