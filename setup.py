"""Setup.py for the videoio package."""

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="perfectVideoCapture",
    version="0.1.1rc",
    author="DataPro",
    author_email="m.komijani@gmail.com",
    description="Perfect RTSP video capture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DataPro-M/perfectVideoCapture",
    project_urls={
        "Bug Tracker": "https://github.com/DataPro-M/perfectVideoCapture/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=["videoio"],
    python_requires=">=3.8",
    entry_points={"console_scripts": ["videoio = videoio.demo:main"]},
)
