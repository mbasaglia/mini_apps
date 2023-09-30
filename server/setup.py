#!/usr/bin/env python3
import pathlib
import setuptools

here = pathlib.Path(__file__).absolute().parent
root = here.parent

with open(root / "README.md", "r", encoding='utf8') as fh:
    long_description = fh.read()


def find_packages(package_root: pathlib.Path):
    paks = [package_root.relative_to(here)]
    for file in package_root.iterdir():
        if file.name == "__pycache__":
            continue

        if file.id_dir():
            paks += find_packages(file)
    return paks


extras_require = {
    "glaximini": ["lottie", "hashids"],
    "mini_events": ["aiocron"],
}

setuptools.setup(
    name="mini-apps",
    version="0.0.1",
    author="Mattia Basaglia",
    author_email="mattia.basaglia@gmail.com",
    description="A framework to implement Telegram mini apps (and other bots)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mbasaglia/mini_apps",
    # package_dir={'': 'lib'},
    license="GNU General Public License v3 or later (GPLv3+)",
    packages=find_packages(here / "mini_apps"),
    scripts=[
        "server.py"
    ],
    keywords="telegram bot",
    # https://pypi.org/classifiers/
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    zip_safe=True,
    requires=[
        "peewee",
        "telethon",
        "websockets",
    ],
    python_requires=">=3",
    extras_require=extras_require,
    # test_suite="test",
    # project_urls={},
)
