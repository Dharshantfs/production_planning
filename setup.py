from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="production_planning",
    version="0.0.1",
    author="Your Company",
    author_email="info@yourcompany.com",
    description="Production Planning and Queuing System for Manufacturing Units",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourcompany/production_planning",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Manufacturing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Framework :: Frappe",
    ],
    python_requires=">=3.7",
    install_requires=[
        "frappe",
    ],
    zip_safe=False,
    include_package_data=True,
)
