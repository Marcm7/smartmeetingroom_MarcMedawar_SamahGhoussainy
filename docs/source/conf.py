import os
import sys

# Project root (two levels up from this file)
sys.path.insert(0, os.path.abspath('../..'))

# Services directory so packages like `bookings_service` are importable
sys.path.insert(0, os.path.abspath('../../services'))

project = 'Smart Meeting Room Backend'
copyright = '2025, Samah Ghoussainy & Marc Medawar'
author = 'Samah Ghoussainy & Marc Medawar'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'  # if this gives an error, run: pip install sphinx_rtd_theme
html_static_path = ['_static']
