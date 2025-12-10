# 📦 Publishing with uv (Quick Guide)

This document provides the **minimal commands** needed to version, build, and publish your package using **uv**.

---

## 🏗️ Build Package

```bash
uv build --no-sources
```

#### OR WITH NO SOURCE

```bash
uv build
```

---

## 🧪 Publish to TestPyPI

Add this to your `pyproject.toml`:

```toml
[[tool.uv.index]]
name = "testpypi"
url = "https://test.pypi.org/simple/"
publish-url = "https://test.pypi.org/legacy/"
explicit = true
```

Publish:

```bash
uv publish --index testpypi --token <TEST_PYPI_API_TOKEN>
```

---

## 🚀 Publish to PyPI

```bash
uv publish --token <PYPI_TOKEN>
```

---

## ✔ Verify Installation

```bash
uv run --with chainless --no-project -- python -c "import chainless"
```