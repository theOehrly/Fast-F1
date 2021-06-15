# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('../'))
from datetime import datetime
import re

# -- Project information -----------------------------------------------------

# load version number from file in sources dir without importing
with open('../fastf1/version.py') as vfobj:
    vstring = str(vfobj.read())
    version = re.search(r"(\d.\d.\d)", vstring)[0]


# project = 'Fast F1'
# copyright = 'MIT'
# author = 'Oehrly'
version = version
release = version
copyright = f'{datetime.now().year}, theOehrly'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'matplotlib.sphinxext.plot_directive',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_rtd_theme',
    'autodocsumm'
]

todo_include_todos = True
autodoc_member_order = 'bysource'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'collapse_navigation': False
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# matplotlib plot directive options
plot_pre_code = "import numpy as np;" \
                "from matplotlib import pyplot as plt;" \
                "import logging;" \
                "logging.getLogger().setLevel(logging.WARNING);" \
                "plt.rcParams['figure.figsize'] = [8.0, 4.5];" \
                "import fastf1;" \
                "fastf1.Cache.enable_cache('../dev_cache');"

plot_html_show_source_link = False
