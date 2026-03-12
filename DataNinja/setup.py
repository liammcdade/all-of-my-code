from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="DataNinja",
    version="0.1.0",
    author="AI Assistant",
    description="A toolkit for data processing, analysis, and utilities.",
    long_description="DataNinja provides a suite of tools for loading, cleaning, analyzing, transforming, and visualizing data, along with various utility plugins.",
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests", "docs", "examples"]
    ),
    include_package_data=True,  # To include non-code files specified in MANIFEST.in (if any)
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dataninja = DataNinja.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",  # Assuming MIT, adjust if different
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
)
