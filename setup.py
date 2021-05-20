import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tornado-tryton",
    version="1.0.2",
    author="James Sparc",
    author_email="jimmysparc@gmail.com",
    description="Adds Tryton support to Tornado application.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TinKurbatoff/tornado-tryton",
    project_urls={
        "Bug Tracker": "https://github.com/TinKurbatoff/tornado-tryton/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
