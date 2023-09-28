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
copyright = (
    f"{datetime.datetime.today().year}, {author}",
)

version = PROJECT_PACKAGE_METADATA["Version"]
release = version

DOCUMENT_DESCRIPTION = f"{project} documentation"


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
]

root_doc = "contents"

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'

html_theme_options = {
    "description": DOCUMENT_DESCRIPTION,
    "github_banner": "true",
    "github_button": "true",
    "github_repo": "mxcubecore",
    "github_user": "mxcube",
}


# EOF
