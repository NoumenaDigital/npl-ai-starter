from setuptools import setup, find_packages

setup(
    name="npl-ai-starter",
    version="0.1.0",
    package_dir={"": "python"},
    packages=find_packages(where="python"),
    python_requires=">=3.8",
)
