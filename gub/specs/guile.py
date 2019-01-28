import os
#
from gub import context
from gub import misc
from gub import loggedos
from gub import octal
from gub import repository
from gub import target
from gub import tools

class Guile (target.AutoBuild):
    # source = 'git://git.sv.gnu.org/guile.git&branch=branch_release-1-8&revision=bba579611b3671c7e4c1515b100f01c048a07935'
    source = 'http://ftp.gnu.org/pub/gnu/guile/guile-1.8.7.tar.gz'
    patches = ['guile-reloc-1.8.6.patch',
               'guile-cexp.patch',
               'guile-1.8.6-test-use-srfi.patch',
               'guile-1.8.7-doc-snarfing.patch']
    dependencies = ['gettext-devel', 'gmp-devel', 'libtool', 'tools::guile']
    guile_configure_flags = misc.join_lines ('''
--without-threads
--with-gnu-ld
--enable-deprecated
--enable-discouraged
--disable-error-on-warning
--enable-relocation
--enable-rpath
''')
    guile_configure_variables = misc.join_lines ('''
have_makeinfo=no
''')
    configure_variables = (target.AutoBuild.configure_variables
                           + misc.join_lines ('''
CC_FOR_BUILD="
LD_PRELOAD=
C_INCLUDE_PATH=
CPPFLAGS=
LIBRARY_PATH=
/usr/bin/cc"
'''))
    # FIXME: guile runs gen_scmconfig [when not x-building also guile]
    # without setting the proper LD_LIBRARY_PATH.
    compile_flags_native = (' LD_PRELOAD= '
                            + ' LD_LIBRARY_PATH=%(tools_prefix)s/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH} '
                            + ' cross_compiling=yes ')
    # FIXME: guile runs gen_scmconfig [when not x-building also guile]
    # without setting the proper LD_LIBRARY_PATH.
    configure_command = ('GUILE_FOR_BUILD=%(tools_prefix)s/bin/guile '
                         + target.AutoBuild.configure_command
                         + guile_configure_flags
                         + guile_configure_variables)
    compile_command = ('preinstguile=%(tools_prefix)s/bin/guile '
                       + target.AutoBuild.compile_command)
    subpackage_names = ['doc', 'devel', 'runtime', '']
    @staticmethod
    def version_from_VERSION (self):
        return self.version_from_shell_script ('GUILE-VERSION',
                                               'GUILE_MAJOR_VERSION',
                                               '%(GUILE_MAJOR_VERSION)s.%(GUILE_MINOR_VERSION)s.%(GUILE_MICRO_VERSION)s',
                                               '1.8.6')
    def __init__ (self, settings, source):
        target.AutoBuild.__init__ (self, settings, source)
        if isinstance (source, repository.Git):
            ##source.version = lambda: '1.8.6'
            source.version = misc.bind_method (Guile.version_from_VERSION,
                                               source)
        self.so_version = '17'
    def patch (self):
        self.dump ('''#!/bin/sh
exec %(tools_prefix)s/bin/guile "$@"
''', "%(srcdir)s/pre-inst-guile.in")
        #self.autopatch ()
        # Guile's texi files can not be compiled by texinfo-6.1.
        self.file_sub ([(r'SUBDIRS = ref tutorial goops r5rs', 'SUBDIRS =')],
                       '%(srcdir)s/doc/Makefile.am')
        self.file_sub ([(r'SUBDIRS = ref tutorial goops r5rs', 'SUBDIRS =')],
                       '%(srcdir)s/doc/Makefile.in')
        target.AutoBuild.patch (self)
    def autopatch (self):
        self.file_sub ([(r'AC_CONFIG_SUBDIRS\(guile-readline\)', '')],
                       '%(srcdir)s/configure.in')
        self.file_sub ([(r'guile-readline', '')],
                       '%(srcdir)s/Makefile.am')
        # Guile [doc] does not compile with dash *and* not with
        # librestrict-stat.so; patch out.
        if isinstance (self.source, repository.Git):
            self.file_sub ([(' doc ', ' ')], '%(srcdir)s/Makefile.am')
            self.file_sub ([('guile-readline', '')], '%(srcdir)s/Makefile.am')
        else:
            self.file_sub ([(' doc ', ' ')], '%(srcdir)s/Makefile.in')
            self.file_sub ([('guile-readline', '')], '%(srcdir)s/Makefile.in')
        self.dump ('', '%(srcdir)s/doc/ref/version.texi')
        self.dump ('', '%(srcdir)s/doc/tutorial/version.texi')
    def compile (self):
        ## Ugh: broken dependencies break parallel build with make -jX
        self.system ('cd %(builddir)s/libguile && make %(compile_flags_native)s gen-scmconfig guile_filter_doc_snarfage')
        # Remove -L %(system_root)s from `guile-config link'
        self.system ('cd %(builddir)s/libguile && make %(compile_flags_native)slibpath.h')
        self.file_sub ([('''-L *%(system_root)s''', '-L')],
                       '%(builddir)s/libguile/libpath.h')
        target.AutoBuild.compile (self)
    def install (self):
        # with 1.8.7: libtool: cannot install directory not ending in...
        # after config.status is being re-run for building of libpath.h
        self.update_libtool ()
        target.AutoBuild.install (self)
        majmin_version = '.'.join (self.expand ('%(version)s').split ('.')[0:2])
        
        self.dump ("prependdir GUILE_LOAD_PATH=$INSTALLER_PREFIX/share/guile/%(majmin_version)s\n",
                   '%(install_prefix)s/etc/relocate/guile.reloc',
                   env=locals ())
        version = self.expand ('%(version)s')
        #FIXME: c&p linux.py
        self.dump ('''\
#! /bin/sh
test "$1" = "--version" && echo "%(target_architecture)s-guile-config - Guile version %(version)s"
#test "$1" = "compile" && echo "-I $%(system_prefix)s/include"
#test "$1" = "link" && echo "-L%(system_prefix)s/lib -lguile -lgmp"
#prefix=$(dirname $(dirname $0))
prefix=%(system_prefix)s
test "$1" = "compile" && echo "-I$prefix/include"
test "$1" = "link" && echo "-L$prefix/lib -lguile -lgmp"
test "$1" = "info" && test "$2" = "guileversion" && echo "%(version)s"
exit 0
''',
             '%(install_prefix)s%(cross_dir)s/bin/%(target_architecture)s-guile-config')
        self.chmod ('%(install_prefix)s%(cross_dir)s/bin/%(target_architecture)s-guile-config', octal.o755)
        self.system ('cd %(install_prefix)s%(cross_dir)s/bin && cp -pv %(target_architecture)s-guile-config guile-config')

class Guile__mingw (Guile):
    def __init__ (self, settings, source):
        Guile.__init__ (self, settings, source)
        # Configure (compile) without -mwindows for console
        self.target_gcc_flags = '-mms-bitfields'
    dependencies = Guile.dependencies +  ['regex-devel']
    configure_flags = (Guile.configure_flags
                       + ' --without-threads')
    configure_variables = (Guile.configure_variables
                           .replace ("':'", "';'")
                + misc.join_lines ('''
CFLAGS='-O2 -DHAVE_CONFIG_H=1 -I%(builddir)s'
'''))
    config_cache_overrides = Guile.config_cache_overrides + '''
scm_cv_struct_timespec=${scm_cv_struct_timespec=no}
guile_cv_func_usleep_declared=${guile_cv_func_usleep_declared=yes}
guile_cv_exeext=${guile_cv_exeext=}
libltdl_cv_sys_search_path=${libltdl_cv_sys_search_path="%(system_prefix)s/lib"}
'''
    def configure (self):
        self.file_sub ([('''^#(LIBOBJS=".*fileblocks.*)''', r'\1')],
                       '%(srcdir)s/configure')
        Guile.configure (self)
        for libtool in ['%(builddir)s/libtool']: # readline patched-out: '%(builddir)s/guile-readline/libtool']:
            self.file_sub ([('-mwindows', '')], libtool)
    def compile (self):
        ## Why the !?#@$ is .EXE only for guile_filter_doc_snarfage?
        self.system ('''cd %(builddir)s/libguile &&make %(compile_flags_native)sgen-scmconfig guile_filter_doc_snarfage.exe''')
        self.system ('cd %(builddir)s/libguile && cp guile_filter_doc_snarfage.exe guile_filter_doc_snarfage')
        Guile.compile (self)
    def install (self):
        Guile.install (self)
        # dlopen-able .la files go in BIN dir, BIN OR LIB package
        self.system ('''mv %(install_prefix)s/lib/lib*[0-9].la %(install_prefix)s/bin''')
        self.system ('''cd %(install_prefix)s/bin && cp guile.exe guile-windows.exe''')

class Guile__linux (Guile):
    compile_command = ('export LD_LIBRARY_PATH=%(builddir)s/libguile/.libs:%(system_prefix)s/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH};'
                + Guile.compile_command)

class Guile__linux__ppc (Guile__linux):
    config_cache_overrides = Guile__linux.config_cache_overrides + '''
guile_cv_have_libc_stack_end=no
'''

class Guile__freebsd (Guile):
    config_cache_overrides = Guile.config_cache_overrides + '''
ac_cv_type_socklen_t=yes
guile_cv_use_csqrt="no"
'''

class Guile__darwin (Guile):
    patches = Guile.patches + ['guile-1.8.6-pthreads-cross.patch']
    def install (self):
        Guile.install (self)
        def dylib_link (logger, fname):
            directory = os.path.split (fname)[0]
            src = os.path.basename (fname)
            dst = os.path.splitext (os.path.basename (fname))[0] + '.so'
            loggedos.symlink (logger, src, os.path.join (directory, dst))
        self.map_locate (dylib_link,
                         self.expand ('%(install_prefix)s/lib/'),
                         'libguile-srfi*.dylib')
    def configure (self):
        self.file_sub ([('guile-readline', '')],
                       '%(srcdir)s/Makefile.in')
        Guile.configure (self)

class Guile__linux__x86 (Guile):
    patches = Guile.patches + ['guile-1.8.6-pthreads-cross.patch']

class Guile__tools (tools.AutoBuild, Guile):
    dependencies = (Guile.dependencies
                    + ['autoconf', 'automake', 'gettext', 'flex', 'libtool'])
    make_flags = Guile.make_flags
    # Doing make gen-scmconfig, guile starts a configure recheck:
    #    cd .. && make  am--refresh
    #    /bin/sh ./config.status --recheck
    # leading to
    #    checking size of char... 0
    # Great idea, let's re-check!  You never know... :-)
    compile_flags_native = misc.join_lines ('''
LD_LIBRARY_PATH=%(system_prefix)s/lib
CFLAGS='-O2 -I%(system_prefix)s/include'
LDFLAGS='-L%(system_prefix)s/lib %(rpath)s'
''')
    configure_command = ('LD_LIBRARY_PATH=%(system_prefix)s/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH} '
                         + tools.AutoBuild.configure_command
                         + Guile.guile_configure_flags
                         + Guile.guile_configure_variables)
    # FIXME: when configuring, guile runs binaries linked against
    # libltdl.
    # FIXME: when not x-building, guile runs gen_scmconfig, guile without
    # setting the proper LD_LIBRARY_PATH.
    compile_command = ('export LD_LIBRARY_PATH=%(builddir)s/libguile/.libs:%(system_prefix)s/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH};'
                + Guile.compile_command)
    def patch (self):
        # Guile's texi files can not be compiled by texinfo-6.1.
        self.file_sub ([(r'SUBDIRS = ref tutorial goops r5rs', 'SUBDIRS =')],
                       '%(srcdir)s/doc/Makefile.am')
        self.file_sub ([(r'SUBDIRS = ref tutorial goops r5rs', 'SUBDIRS =')],
                       '%(srcdir)s/doc/Makefile.in')
        tools.AutoBuild.patch (self)
        #Guile.autopatch (self)
    def install (self):
        tools.AutoBuild.install (self)
        self.system ('cd %(install_root)s%(packaging_suffix_dir)s%(prefix_dir)s/bin && cp guile guile-1.8')
        self.file_sub ([('[(]string-join other-flags[)]', '(string-join (filter (lambda (x) (not (equal? x "-L/usr/lib"))) other-flags))')],
                       '%(install_root)s%(packaging_suffix_dir)s%(prefix_dir)s/bin/guile-config',
                       must_succeed=True)
