import re
#
from gub import build
from gub import context
from gub import misc
from gub import target
from gub import tools

class Python (target.AutoBuild):
    source = 'https://www.python.org/ftp/python/2.4.5/Python-2.4.5.tar.bz2'
    #source = 'https://www.python.org/ftp/python/2.4.2/Python-2.4.2.tar.bz2'
    patches_242 = [
        'python-2.4.2-1.patch',
        'python-configure.in-posix.patch&strip=0',
        'python-configure.in-sysname.patch&strip=0',
        'python-2.4.2-configure.in-sysrelease.patch',
        'python-2.4.2-setup.py-import.patch&strip=0',
        'python-2.4.2-setup.py-cross_root.patch&strip=0',
        'python-2.4.2-fno-stack-protector.patch',
        ]

    patches = [
        'python-2.4.5-1.patch',
        'python-configure.in-posix.patch&strip=0',
        'python-2.4.5-configure.in-sysname.patch',
        'python-2.4.2-configure.in-sysrelease.patch',
        'python-2.4.2-setup.py-import.patch&strip=0',
        'python-2.4.2-setup.py-cross_root.patch&strip=0',
#        'python-2.4.2-fno-stack-protector.patch',
        'python-2.4.5-python-2.6.patch',
        'python-2.4.5-native.patch',
        'python-2.4.5-db4.7.patch',
        ]
    dependencies = ['db-devel', 'expat-devel', 'zlib-devel', 'tools::python']
    force_autoupdate = True
    subpackage_names = ['doc', 'devel', 'runtime', '']
    so_modules = [
        'itertools',
        'struct',
        'time',
        ]
    make_flags = misc.join_lines (r'''
BLDLIBRARY='%(rpath)s -L. -lpython$(VERSION)'
''')
    def __init__ (self, settings, source):
        target.AutoBuild.__init__ (self, settings, source)
        self.CROSS_ROOT = '%(targetdir)s'
        if 'stat' in misc.librestrict ():
            self.install_command = ('LIBRESTRICT_ALLOW=/usr/lib/python2.4/lib-dynload:${LIBRESTRICT_ALLOW-/foo} '
                + target.AutoBuild.install_command)
    def patch (self):
        target.AutoBuild.patch (self)
        self.file_sub ([('@CC@', '@CC@ -I$(shell pwd)')],
                        '%(srcdir)s/Makefile.pre.in')
    def autoupdate (self):
        target.AutoBuild.autoupdate (self)
        # FIXME: REMOVEME/PROMOTEME to target.py?
        if self.settings.build_platform == self.settings.target_platform:
            self.file_sub ([('cross_compiling=(maybe|no|yes)',
                             'cross_compiling=no')], '%(srcdir)s/configure')
    def install (self):
        target.AutoBuild.install (self)
        misc.dump_python_config (self)
        def assert_fine (logger):
            dynload_dir = self.expand ('%(install_prefix)s/lib/python%(python_version)s/lib-dynload')
            so = self.expand ('%(so_extension)s')
            all = [x.replace (dynload_dir + '/', '') for x in misc.find_files (dynload_dir, '.*' + so)]
            failed = [x.replace (dynload_dir + '/', '') for x in misc.find_files (dynload_dir, '.*failed' + so)]
            if failed:
                logger.write_log ('failed python modules:' + ', '.join (failed), 'error')
            for module in self.so_modules:
                if not module + so in all:
                    logger.write_log ('all python modules:' + ', '.join (all), 'error')
                    raise Exception ('Python module failed: ' + module)
        self.func (assert_fine)
    ### Ugh.
    @context.subst_method
    def python_version (self):
        return '.'.join (self.version ().split ('.')[0:2])

class Python__mingw_binary (build.BinaryBuild):
    source = 'http://lilypond.org/~hanwen/python-2.4.2-windows.tar.gz'

    def python_version (self):
        return '2.4'

    def install (self):
        build.BinaryBuild.install (self)
        self.system ('''
cd %(install_root)s && mkdir usr && mv Python24/include usr
cd %(install_root)s && mkdir -p usr/bin/ && mv Python24/* usr/bin
rmdir %(install_root)s/Python24
''')

class Python__freebsd (Python):
    def configure (self):
        Python.configure (self)
        self.file_sub ([
                ('^LDSHARED=.*', 'LDSHARED = $(CC) -shared'),
                ('BLDSHARED=.*', 'BLDSHARED = $(CC) -shared'),
                ], '%(builddir)s/Makefile')

class Python__mingw (Python):
    patches = Python.patches + [
        'python-2.4.2-winsock2.patch',
        'python-2.4.2-setup.py-selectmodule.patch',
        'python-2.4.5-disable-pwd-mingw.patch',
        'python-2.4.5-mingw-site.patch',
        'python-2.4.5-mingw-socketmodule.patch',
        ]
    config_cache_overrides = (Python.config_cache_overrides
                              #FIXME: promoteme? see Gettext/Python
                              .replace ('ac_cv_func_select=yes',
                                        'ac_cv_func_select=no')
                              + '''
ac_cv_pthread_system_supported=yes,
ac_cv_sizeof_pthread_t=12
''')
    def __init__ (self, settings, source):
        Python.__init__ (self, settings, source)
        self.target_gcc_flags = '-DMS_WINDOWS -DPy_WIN_WIDE_FILENAMES -I%(system_prefix)s/include' % self.settings.__dict__
    dependencies = Python.dependencies + ['mingw-w64-runtime-winpthread-dll']
    # FIXME: first is cross compile + mingw patch, backported to
    # 2.4.2 and combined in one patch; move to cross-Python?
    def patch (self):
        Python.patch (self)
        self.file_sub ([
                ('(== "win32")', r'in ("win32", "mingw32")'),
                ], "%(srcdir)s/Lib/subprocess.py",
                       must_succeed=True)
    def configure (self):
        Python.configure (self)
        self.dump ('''
_subprocess ../PC/_subprocess.c
msvcrt ../PC/msvcrtmodule.c
''',
                   '%(builddir)s/Modules/Setup',
                   mode='a')
    def compile (self):
        self.system ('''
cd %(builddir)s && rm -f python.exe
''')
        Python.compile (self)
        self.system ('''
cd %(builddir)s && mv python.exe python-console.exe
cd %(builddir)s && make LINKFORSHARED='-mwindows'
cd %(builddir)s && mv python.exe python-windows.exe
cd %(builddir)s && cp -p python-console.exe python.exe
''')
    def install (self):
        Python.install (self)
        self.system ('''
cd %(builddir)s && cp -p python-windows.exe python-console.exe %(install_prefix)s/bin
''')
        self.file_sub ([('extra = ""', 'extra = "-L%(system_prefix)s/bin -L%(system_prefix)s/lib -lpython2.4 -lpthread"')],
                       '%(install_prefix)s%(cross_dir)s/bin/python-config')

        def rename_so (logger, fname):
            dll = re.sub ('\.so*', '.dll', fname)
            loggedos.rename (logger, fname, dll)

        self.map_locate (rename_so,
                         self.expand ('%(install_prefix)s/lib/python%(python_version)s/lib-dynload'),
                                      '*.so*')
        ## UGH.
        self.system ('''
cp %(install_prefix)s/lib/python%(python_version)s/lib-dynload/* %(install_prefix)s/bin
''')
        self.system ('''
chmod 755 %(install_prefix)s/bin/*
''')
        # This builds and runs in wine, but produces DLLs that
        # do not load in Windows Vista
        if 0:
            self.generate_dll_a_and_la ('python2.4', '-lpthread')

class Python__tools (tools.AutoBuild, Python):
    patches = [
#        'python-2.4.2-fno-stack-protector.patch',
        'python-2.4.5-readline.patch', # Stop python from reading ~/.inputrc
        'python-2.4.5-db4.7.patch',
        'python-2.4.5-regen.patch',
        'python-2.4.5-gcc-R.patch',
        'python-2.4.5-Setup-crypt.patch',
        'python-2.4.5-Setup-dbm.patch',
        ]
    dependencies = [
        'autoconf',
        'db', # _bsddb
        'libtool',
        ]
    force_autoupdate = True
    parallel_build_broken = True
    # Use gcc-7 if it is available. Python 2.4.5 seems to incompatible to gcc-8!
    # LD_LIBRARY_PATH and python wrapper script are needed for ubuntu 18.04
    configure_command = ('if [ "A`which gcc-7 2>>/dev/null`" != "A" ]; then export CC=gcc-7 ; fi; '
                         +'LD_LIBRARY_PATH=%(system_prefix)s/lib '
                         + tools.AutoBuild.configure_command)
    compile_command = ('LD_LIBRARY_PATH=%(system_prefix)s/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH} '
                         + tools.AutoBuild.compile_command)
    install_command = ('LD_LIBRARY_PATH=%(system_prefix)s/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH} '
                         + tools.AutoBuild.install_command)
    make_flags = Python.make_flags + ' LIBC="-lcrypt -ldb" '
    def patch (self):
        Python.patch (self)
    def install (self):
        Python.install (self)
        self.system ('''
mv %(install_prefix)s/bin/python %(install_prefix)s/bin/_python
echo '#!/bin/sh' > %(install_prefix)s/bin/python
echo 'LD_LIBRARY_PATH=%(system_prefix)s/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH} %(system_prefix)s/bin/_python "$@"' >> %(install_prefix)s/bin/python
chmod 755 %(install_prefix)s/bin/python
''')
