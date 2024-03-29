from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

setup(
    name="dboost_py",
    version="0.0.1",
    author="Andrew Butler",
    author_email="",
    description="Gradient boosting convex cone predict and optimize.",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/butl3ra/",
    packages=find_packages(),
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3.9",
    ],
)
