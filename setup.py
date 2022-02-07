import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


packages = setuptools.find_packages(include=["gasofo*"])


setuptools.setup(
    name="gasofo",
    version="2.0.0",
    author="Shawn Chin",
    author_email="shawn@qwil.io",
    description="Qwil's hexagonal architecture framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/QwilApp/gasofo",
    packages=packages,
    install_requires=[],
    python_requires='>=3.6',
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
