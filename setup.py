from setuptools import setup, find_packages

setup(
    name="pdf-duplicator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pypdf>=4.0.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "pdf-duplicator=pdf_duplicator.cli:cli",
        ],
    },
    python_requires=">=3.9",
)
