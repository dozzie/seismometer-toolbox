#-----------------------------------------------------------------------------
#
# Sphinx configuration for Seismometer Toolbox project
#
#-----------------------------------------------------------------------------

project = u'Seismometer Toolbox'

#copyright = u'...'

release = '0.4.0'
version = '0.4'

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

html_theme = 'poole'
html_theme_path = ['themes']

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
    ('manpages/hailerter', 'hailerter',
     'state tracker and notification generator',
     [], 8),
    ('manpages/seismometer-message', 'seismometer-message',
     'Seismometer message format',
     [], 7),
]

#man_show_urls = False

#-----------------------------------------------------------------------------
# vim:ft=python
