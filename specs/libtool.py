import targetpackage
from toolpackage import Tool_package

# FIXME, need for WITH settings when building dependency 'libtool'
# This works without libtool.py:
#    ./gub-builder.py -p mingw build http://ftp.gnu.org/pub/gnu/libtool/libtool-1.5.20.tar.gz

class Libtool (targetpackage.Target_package):
    def __init__ (self, settings):
        targetpackage.Target_package.__init__ (self, settings)
        self.with (version='1.5.20')


class Libtool__darwin (Libtool):
    def install (self):
        Libtool.install (self)

        ## necessary for programs that load dynamic modules.
        self.dump ("prependdir DYLD_LIBRARY_PATH=$INSTALLER_PREFIX/lib",
                   '%(install_root)s/usr/etc/relocate/libtool.reloc')


class Libtool__local (Tool_package):
    """

Libtool as a local package is rather painful, as Darwin has its own
libtool which is unrelated to GNU libtool, but necessary for linking
dylibs.
    
    """
    
    def __init__ (self, settings):
        Tool_package.__init__ (self, settings)
        self.with (version='1.5.20')
