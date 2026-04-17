from setuptools import setup, find_packages

setup(
    name="deerflow-chromadb",
    version="0.1.0",
    description="ChromaDB memory storage integration for DeerFlow",
    packages=find_packages(),
    install_requires=[
        "chromadb>=0.5.0",
        "deerflow-harness>=0.1.0",
    ],
    entry_points={
        "deerflow.memory_storage": [
            "chromadb=chromadb.storage:ChromaMemoryStorage",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.12',
)
