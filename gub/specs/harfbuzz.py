from gub import misc
from gub import target
from gub import tools

class Harfbuzz (target.AutoBuild):
    source = 'https://www.freedesktop.org/software/harfbuzz/release/harfbuzz-1.3.0.tar.bz2'
    dependencies = [
        'tools::bzip2',
        'freetype-devel',
        'glib-devel',
    ]
    configure_flags = (target.AutoBuild.configure_flags
                       + misc.join_lines ('''
--without-cairo
--without-icu
'''))

class Harfbuzz__tools (tools.AutoBuild, Harfbuzz):
    pass
