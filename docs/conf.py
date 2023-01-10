# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('../'))
import os.path
from datetime import datetime
import re

# -- Project information -----------------------------------------------------

# load version number from file in sources dir without importing
with open('../fastf1/version.py') as vfobj:
    vstring = str(vfobj.read())
    version = re.search(r"(\d+.\d+.\d+[-\w]*)", vstring)[0]


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
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
    'sphinx.ext.autosummary',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx_gallery.gen_gallery',
    'autodocsumm',
    'fastf1.ergast.sphinx',
]

todo_include_todos = True
autodoc_member_order = 'bysource'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    '../fastf1/signalr_aio'
]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'furo'
html_theme_options = {
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
html_css_files = [
    'css/custom.css',
]

doc_cache = os.path.abspath('../doc_cache')
# matplotlib plot directive options
plot_pre_code = f"import numpy as np;" \
                f"from matplotlib import pyplot as plt;" \
                f"plt.rcParams['figure.figsize'] = [8.0, 4.5];" \
                f"import fastf1;" \
                f"fastf1.Cache.enable_cache('{doc_cache}');" \
                f"import logging;" \
                f"logging.getLogger().setLevel(logging.WARNING);"

plot_include_source = True
plot_html_show_source_link = False

# doctest directive options
doctest_global_setup = f"import fastf1;" \
                       f"fastf1.Cache.enable_cache('{doc_cache}');" \
                       f"import logging;" \
                       f"logging.getLogger().setLevel(logging.WARNING);"


# sphinx gallery configuration
sphinx_gallery_conf = {
    'examples_dirs': '../examples',
    'gallery_dirs': 'examples_gallery',
    'download_all_examples': False,
    'remove_config_comments': True,
}

# options for latexpdf build
latex_elements = {
    'preamble': r'\usepackage{enumitem}\setlistdepth{99}',
}
