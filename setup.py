from setuptools import setup, find_packages

setup(
    name="WedgieIntegrator",
    version="0.1.1.0",
    author="Chad Roberts",
    author_email="jcbroberts@gmail.com",
    description="An API client toolkit that is async friendly",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/deathbywedgie/WedgieIntegrator",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[
        "httpx",
        "pydantic",
        "tenacity",
        "structlog"
    ],
)
