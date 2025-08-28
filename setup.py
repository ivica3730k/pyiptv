from setuptools import find_packages, setup

setup(
    name="pyiptv",
    version="0.1.0",
    description="A simple IPTV player ",
    packages=find_packages(exclude=("tests", "tests.*", "venv")),
    python_requires=">=3.12",
    install_requires=[
        "requests",
        "prompt-toolkit",
        "rich",
        "python-dotenv",
    ],
    extras_require={
        "dev": [
            "black",
            "pytest",
            "isort",
        ]
    },
    entry_points={
        "console_scripts": [
            "pyiptv=pyiptv.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
)
