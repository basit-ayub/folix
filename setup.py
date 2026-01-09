from setuptools import setup

setup(
    name="folix",
    license="MIT",
    license_files=[],
    version="1.0.0",
    description="A smart PDF splitter that uses AI to extract chapters.",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Abdul Basit",
    author_email="a.basitayub2004@gmail.com",
    url="https://github.com/basit-ayub/folix",
    py_modules=["folix"],
    install_requires=[
        "pymupdf",
        "mistralai",
        "argparse",
        "json",
    ],
    entry_points={
        "console_scripts": [
            "folix=folix:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)