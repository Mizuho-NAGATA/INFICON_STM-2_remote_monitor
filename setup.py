"""
Setup configuration for STM2-remote package.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="stm2-remote",
    version="1.0.0",
    author="NAGATA Mizuho",
    author_email="",
    description="Remote monitoring system for INFICON STM-2 thin film deposition monitor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Mizuho-NAGATA/STM2-remote",
    py_modules=["STM2-remote-monitor"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
)
