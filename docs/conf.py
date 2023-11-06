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
root = here.parent
auto_path = root / "src"
sys.path.append(str(auto_path))


def make_doc_file(module, dst_path, title=None):
    with open(str(dst_path) + ".rst", "w") as f:
        title = "``%s``" % (title or module)
        f.write("%s\n%s\n\n" % (title, "=" * len(title)))
        f.write(".. automodule:: %s\n" % module)
        f.write("  :show-inheritance:\n")
        f.write("  :members:\n")


def make_doc_files(module, src_path: pathlib.Path, dst_path: pathlib.Path):
    if src_path.is_dir():
        if src_path.name == "__pycache__":
            return
        for child in src_path.iterdir():
            dst_path.mkdir(exist_ok=True)
            make_doc_files(module + "." + child.stem, child, dst_path / child.stem)
    elif src_path.suffix == ".py":
        make_doc_file(module, dst_path)


make_doc_files("mini_apps", auto_path / "mini_apps", here / "mini_apps")


sys.path.append(str(here))
import js_to_py
pyjs_path = here / "pyjs" / "src"
sys.path.append(str(pyjs_path.parent))
js_source = root / "src" / "mini_apps" / "apps" / "mini_apps" / "public" / "src"
pyjs_path.mkdir(parents=True, exist_ok=True)
dest_path = here / "js"
dest_path.mkdir(exist_ok=True)

for file in js_source.iterdir():
    if file.suffix == ".js":
        with open(file) as f:
            py = js_to_py.js_file_to_py(f.read())
        with open(pyjs_path / (file.stem + ".py"), "w") as f:
            f.write(py)
        make_doc_file("src." + file.stem, dest_path / file.stem, file.stem)


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinxarg.ext",
]

templates_path = ['_templates']
exclude_patterns = []

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["static"]
html_css_files = [
    "custom.css",
]
