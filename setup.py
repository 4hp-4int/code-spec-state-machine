#!/usr/bin/env python3
"""Setup script for agentic-spec package."""

from pathlib import Path

from setuptools import find_packages, setup

# Read README file
readme_path = Path(__file__).parent / "README.md"
long_description = (
    readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
)

setup(
    name="agentic-spec",
    version="0.1.0",
    description="AI-powered programming specification generator with inheritance and review workflows",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Khalen Fredieu",
    author_email="khalen@4hp-4int.com",
    packages=find_packages(),
    package_data={
        "agentic_spec": ["templates/*.yaml"],
    },
    include_package_data=True,
    install_requires=[
        "PyYAML>=6.0",
    ],
    extras_require={
        "ai": ["openai>=1.96.1"],
        "dev": ["pytest>=7.0", "black>=22.0", "flake8>=4.0"],
    },
    entry_points={
        "console_scripts": [
            "agentic-spec=agentic_spec.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Documentation",
    ],
    keywords="ai programming specification generator development workflow",
)
