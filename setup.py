from setuptools import setup, find_packages

setup(
    name="gatsim",
    version="0.1.0",
    packages=find_packages(),
    description="GATSIM package",
    author="Qi Liu",
    author_email="liuqi_tj@hotmail.com",
    install_requires=[
        # e.g., "numpy>=1.18.0",
        # "matplotlib>=3.1.0",
    ],
    python_requires=">=3.9",
)