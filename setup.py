from setuptools import find_packages, setup


setup(
    name="Sonoran.py",
    version="0.1.0",
    description="Python SDK for Sonoran CAD integrations",
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7",
)
