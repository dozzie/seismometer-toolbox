#-----------------------------------------------------------------------------
#
# Sphinx configuration for Seismometer Toolbox project
#
#-----------------------------------------------------------------------------

project = u'Seismometer Toolbox'

#copyright = u'...'

release = '0.3.0'
version = '0.3'

#-----------------------------------------------------------------------------

# minimal Sphinx version
#needs_sphinx = '1.0'

extensions = ['sphinx.ext.autodoc']

master_doc = 'index'
source_suffix = '.rst'
exclude_trees = ['html', 'man']

#-----------------------------------------------------------------------------
# configuration specific to Python code
#-----------------------------------------------------------------------------

import sys, os
sys.path.insert(0, os.path.abspath('../lib'))

# ignored prefixes for module index sorting
modindex_common_prefix = ["seismometer."]

# documentation for constructors: docstring from class, constructor, or both
autoclass_content = 'both'

#-----------------------------------------------------------------------------
# HTML output
#-----------------------------------------------------------------------------

import sphinx
def ver(v):
    return [int(i) for i in v.split('.')]

if ver(sphinx.__version__) >= ver('1.3'):
    html_theme = 'classic'
else:
    html_theme = 'default'

pygments_style = 'sphinx'

#html_static_path = ['static']

#-----------------------------------------------------------------------------
# TROFF/man output
#-----------------------------------------------------------------------------

man_pages = [
    ('manpages/daemonshepherd', 'daemonshepherd',
     'daemon supervisor and restarter',
     [], 8),
    ('manpages/dumbprobe', 'dumb-probe',
     'monitoring probe',
     [], 8),
    ('manpages/messenger', 'messenger',
     'monitoring and log message transporter',
     [], 8),
]

#man_show_urls = False

#-----------------------------------------------------------------------------
# vim:ft=python
