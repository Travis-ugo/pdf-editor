from setuptools import setup, find_packages

setup(
    name="pdf-duplicator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pypdf[crypto]>=4.0.0",
        "click>=8.0.0",
        "Flask>=3.0",
        "PyMuPDF>=1.24",
        "reportlab>=4.0",
        "Pillow>=10.0",
        "markdown>=3.5",
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "pdf-duplicator=pdf_duplicator.cli:cli",
        ],
    },
    python_requires=">=3.9",
)
