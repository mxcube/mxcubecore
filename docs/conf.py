#


# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


import datetime
import importlib.metadata

PROJECT_PACKAGE_NAME = "mxcubecore"
PROJECT_PACKAGE_METADATA = importlib.metadata.metadata(PROJECT_PACKAGE_NAME)


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "MXCuBE-Core"
author = PROJECT_PACKAGE_METADATA["Author"]
copyright = (f"{datetime.datetime.today().year}, {author}",)

version = PROJECT_PACKAGE_METADATA["Version"]
release = version


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

root_doc = "contents"

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"


# -- Extensions --------------------------------------------------------------


# -- Options for sphinx.ext.autodoc
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

extensions.append("sphinx.ext.autodoc")

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}

autodoc_typehints = "both"


# -- Options for sphinx.ext.autosummary
# https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html

extensions.append("sphinx.ext.autosummary")

autosummary_generate = True


# -- Options for sphinx.ext.intersphinx
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

extensions.append("sphinx.ext.intersphinx")

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
}


# -- Options for sphinx.ext.napoleon
# https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html

# We use Google style docstrings
# https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings

extensions.append("sphinx.ext.napoleon")

napoleon_numpy_docstring = False


# -- Options for sphinx.ext.viewcode
# https://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html

extensions.append("sphinx.ext.viewcode")


# -- Options for myst_parser

extensions.append("myst_parser")

myst_enable_extensions = ("fieldlist",)


# -- Options for sphinx_last_updated_by_git
# https://pypi.org/project/sphinx-last-updated-by-git/

extensions.append("sphinx_last_updated_by_git")


# EOF
