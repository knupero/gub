from gub import tools

class M4__tools (tools.AutoBuild):
    source = 'http://ftp.gnu.org/pub/gnu/m4/m4-1.4.18.tar.xz'
    dependencies = ['tools::xzutils']
    patches = ['m4-1.4.18-glibc-change-work-around.patch']
    config_cache_overrides = tools.AutoBuild.config_cache_overrides + '''
gl_cv_lib_sigsegv=${gl_cv_lib_sigsegv=no}
'''
    def config_cache_settings (self):
        # tools return '' by default, to allow MI
        return self.config_cache_overrides
