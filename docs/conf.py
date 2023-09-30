# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import pathlib
import sys

project = 'Mini Apps'
copyright = '2023, Mattia "Glax" Basaglia'
author = 'Mattia "Glax" Basaglia'


here = pathlib.Path(__file__).absolute().parent
auto_path = here.parent / "server"
sys.path.append(str(auto_path))

def make_doc_files(module, src_path: pathlib.Path, dst_path: pathlib.Path, all_modules):
    if src_path.is_dir():
        if src_path.name == "__pycache__":
            return
        for child in src_path.iterdir():
            dst_path.mkdir(exist_ok=True)
            make_doc_files(module + "." + child.stem, child, dst_path / child.stem, all_modules)
    elif src_path.suffix == ".py":
        all_modules.append(module)
        with open(str(dst_path) + ".rst", "w") as f:
            title = "``%s``" % module
            f.write("%s\n%s\n\n" % (title, "=" * len(title)))
            f.write(".. automodule:: %s\n" % module)
            f.write("  :members:\n")


all_modules = []
make_doc_files("mini_apps", auto_path / "mini_apps", here / "mini_apps", all_modules)


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["myst_parser", "sphinx.ext.autodoc"]

templates_path = ['_templates']
exclude_patterns = []

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = []
