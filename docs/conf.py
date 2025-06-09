# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------

project = 'MSFW - Modular Microservices Framework'
copyright = '2024, MSFW Team'
author = 'MSFW Team'
release = '0.1.0'

# -- General configuration ---------------------------------------------------

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.githubpages',
    'sphinx_copybutton',
    'sphinx.ext.intersphinx',
]

# Source parsers
source_suffix = ['.rst', '.md']

# MyST parser configuration
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "replacements",
    "smartquotes",
    "substitution",
    "tasklist",
]

# Autodoc configuration
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'fastapi': ('https://fastapi.tiangolo.com', None),
    'sqlalchemy': ('https://docs.sqlalchemy.org/en/20/', None),
}

# Internationalization
language = 'en'  # Default language
locale_dirs = ['locales/']
gettext_compact = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'README.md', 'de', 'de/**']

# -- Options for HTML output -------------------------------------------------

html_theme = 'furo'

html_theme_options = {
    "sidebar_hide_name": False,
    "light_logo": "logo-light.png",
    "dark_logo": "logo-dark.png",
    "light_css_variables": {
        "color-brand-primary": "#2563eb",  # Modernes Blau
        "color-brand-content": "#2563eb",
        "color-admonition-background": "#f8fafc",
        "color-sidebar-background": "#ffffff",
        "color-sidebar-background-border": "#e2e8f0",
        "font-stack": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "font-stack--monospace": "'JetBrains Mono', 'Fira Code', Monaco, Consolas, monospace",
    },
    "dark_css_variables": {
        "color-brand-primary": "#60a5fa",  # Helleres Blau für Dark Mode
        "color-brand-content": "#60a5fa",
        "color-admonition-background": "#1e293b",
        "color-sidebar-background": "#0f172a",
        "color-sidebar-background-border": "#334155",
    },
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/Scharxi/msfw",  # Zu Ihrer GitHub URL ändern
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,
            "class": "",
        },
    ],
    "source_repository": "https://github.com/Scharxi/msfw/",  # Zu Ihrer GitHub URL ändern
    "source_branch": "main",
    "source_directory": "docs/",
    "navigation_with_keys": True,
    "top_of_page_button": "edit",
}

html_static_path = ['_static']
html_css_files = ['custom.css']

html_logo = None
html_favicon = None

html_title = "MSFW Documentation"
html_short_title = "MSFW"

# Social media preview
html_meta = {
    "description": "Modular Microservices Framework - Modern Python FastAPI Development",
    "keywords": "Python, FastAPI, Microservices, Framework, API",
    "author": "MSFW Team",
}

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '11pt',
    'preamble': r'''
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[english]{babel}
''',
}

latex_documents = [
    ('index', 'msfw.tex', 'MSFW Documentation',
     'MSFW Team', 'manual'),
]

# -- Options for manual page output ------------------------------------------

man_pages = [
    ('index', 'msfw', 'MSFW Documentation',
     [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------

texinfo_documents = [
    ('index', 'msfw', 'MSFW Documentation',
     author, 'msfw', 'Modular Microservices Framework',
     'Miscellaneous'),
]

# -- Extension configuration -------------------------------------------------

# Todo extension
todo_include_todos = True

# Copy button configuration
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True
copybutton_line_continuation_character = "\\" 