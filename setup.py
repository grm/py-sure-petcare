import setuptools
from os.path import splitext, basename
from glob import glob
from subprocess import check_output, CalledProcessError

with open("README.md", "r") as fh:
    long_description = fh.read()


# Get git version (from https://github.com/pyfidelity/setuptools-git-version)
command = "git describe --tags --long --dirty"
fmt = "{tag}.{commitcount}+{gitsha}"


def format_version(version, fmt=fmt):
    parts = version.split("-")
    assert len(parts) in (3, 4)
    dirty = len(parts) == 4
    tag, count, sha = parts[:3]
    if count == "0" and not dirty:
        return tag
    return fmt.format(tag=tag, commitcount=count, gitsha=sha.lstrip("g"))


def get_git_version():
    try:
        git_version = check_output(command.split()).decode("utf-8").strip()
        return format_version(version=git_version)
    except CalledProcessError:
        return "0.1.0"


tests_require = ["pytest>=3.6", "coverage", "pytest-cov", "requests_mock"]


setuptools.setup(
    name="py-sure-petcare",
    version=get_git_version(),
    author="Jérémie Klein",
    author_email="grm.klein@gmail.com",
    description="This library aims to provide python way to communicate "
    "with sure-petcare systems.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/grm/py-sure-petcare",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    install_requires=["requests"],
    setup_requires=["pytest-runner"],
    tests_require=tests_require,
    extras_require={"dev": ["pre-commit"]},
    py_modules={splitext(basename(path))[0] for path in glob("src/*py")},
    license="GPL",
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
