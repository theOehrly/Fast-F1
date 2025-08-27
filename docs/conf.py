# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('../'))

import os.path
import sys
import warnings
from datetime import datetime

import plotly.io as pio
from plotly.io._sg_scraper import plotly_sg_scraper

import fastf1


sys.path.append(os.path.abspath('extensions'))


ERGAST_BACKEND_OVERRIDE = os.environ.get("FASTF1_DOCS_ERGAST_BACKEND_OVERRIDE")

if ERGAST_BACKEND_OVERRIDE:
    import fastf1.ergast

    fastf1.ergast.interface.BASE_URL = ERGAST_BACKEND_OVERRIDE


# -- FastF1 specific config --------------------------------------------------
# ignore warning on import of fastf1.api
warnings.filterwarnings(action='ignore',
                        message=r'`fastf1.api` will be considered private .*')
warnings.filterwarnings(action='ignore',
                        message=r'`utils.delta_time` is considered '
                                r'deprecated.*')
warnings.filterwarnings(action='ignore',
                        message=r'(COMPOUND_COLORS|DRIVER_COLORS|'
                                r'DRIVER_TRANSLATE|TEAM_COLORS|TEAM_TRANSLATE|'
                                r'COLOR_PALETTE) is deprecated and.*')

doc_cache = os.path.abspath('../doc_cache')


# -- Project information -----------------------------------------------------

project = 'FastF1'
# copyright = 'MIT'
# author = 'Oehrly'
version = fastf1.__version__
release = version
copyright = f'{datetime.now().year}, Philipp Schäfer'
html_title = f"{project} <small>{release}</small>"

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
    'nitpick_ignore_files',
    'notfound.extension',
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

nitpicky = True

nitpick_ignore_regex = [
    (r'py:class', r'collections.abc\..*'),
    (r'py:data', r'typing\..*'),
    (r'py:.*', r'datetime\..*'),
    (r'py:.*', r'pandas\..*'),
    (r'py:.*', r'pd\..*'),
    (r'py:.*', r'numpy\..*'),
    (r'py:.*', r'matplotlib\..*'),
    (r'py:mod', r'logging'),
    (r'py:class', r'logging.Logger'),
]

nitpick_ignore_files = [
    # exclude changelog from nitpick, old entries might reference removed
    # functionality
    r'changelog/.*',
]
# nitpick_ignore_files is a custom extension (docs/extensions)


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "footer_center": ["goatcounter"],
    "secondary_sidebar_items": ["versioning",
                                "page-toc",
                                # "sourcelink",
                                "support_link"],
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/theOehrly/Fast-F1",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        }
    ]
}
html_logo = "_static/banner.png"
html_favicon = "_static/favicon.png"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
html_css_files = [
    'css/custom.css',
]

# -- Plotly configuration ----------------------------------------------------
# use sphinx to render plotly
pio.renderers.default = 'sphinx_gallery_png'


# -- matplotlib plot directive options ---------------------------------------
plot_pre_code = f"import numpy as np;" \
                f"from matplotlib import pyplot as plt;" \
                f"plt.rcParams['figure.figsize'] = [8.0, 4.5];" \
                f"import fastf1;" \
                f"import fastf1.logger;" \
                f"fastf1.Cache.enable_cache('{doc_cache}');" \
                f"fastf1.logger.set_log_level('WARNING');"

plot_include_source = True
plot_html_show_source_link = False


# -- doctest directive options -----------------------------------------------
doctest_global_setup = f"import fastf1;" \
                       f"import fastf1.logger;" \
                       f"fastf1.Cache.enable_cache('{doc_cache}');" \
                       f"fastf1.logger.set_log_level('WARNING');"


# -- sphinx gallery configuration --------------------------------------------
def sphinx_gallery_setup(gallery_conf, fname):
    import fastf1
    import fastf1.logger
    fastf1.Cache.enable_cache(doc_cache)
    fastf1.logger.set_log_level('WARNING')


sphinx_gallery_conf = {
    'examples_dirs': '../examples',
    'gallery_dirs': 'gen_modules/examples_gallery',
    'download_all_examples': False,
    'remove_config_comments': True,
    'image_scrapers': ('matplotlib',  # default
                       plotly_sg_scraper),  # for plotly thumbnail
    'reset_modules': ('matplotlib', 'seaborn',  # defaults
                      sphinx_gallery_setup),  # custom setup
    # directory where function/class granular galleries are stored
    'backreferences_dir': 'gen_modules/backreferences',

    # if an example does not produce an output plot, use the following image
    # as the thumbnail.
    'default_thumb_file': '_static/logo.png',

    # Modules for which function/class level galleries are created. In
    # this case sphinx_gallery and numpy in a tuple of strings.
    'doc_module': ('fastf1', ),
}


# -- options for latexpdf build ----------------------------------------------
latex_elements = {
    'preamble': r'\usepackage{enumitem}\setlistdepth{99}',
}
