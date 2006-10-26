import misc
import os
import re
import md5
import locker
import time
import urllib

## note: repository.py still being used by test-gub, so don't
## throw this overboard yet.
##
class Repository: 
    def __init__ (self):
        self.system = misc.system
        self.read_pipe = misc.read_pipe
        
    def download (self):
        assert 0 

    def get_checksum (self):
        assert 0

    def get_file_content (self):
        ## TODO
        
        return
    
    def update_workdir (self, destdir):
        assert 0
    
class GitRepository (Repository):
    def __init__ (self, git_dir, source='', branch='', revision=''):
        Repository.__init__ (self)
        self.repo_dir = git_dir
        self.checksums = {}
        self.branch = branch
        self.revision = revision
        self.source = source
        
    def __repr__ (self):
        return '#<GitRepository %s>' % self.repo_dir
    
    def get_branches (self):
        branch_lines = self.read_pipe (self.git_command () + ' branch -l ').split ('\n')

        branches =  [b[2:] for b in branch_lines]
        return [b for b in branches if b]
        
    def git (self, cmd, dir='', ignore_error=False):
        cmd = 'GIT_OBJECT_DIRECTORY=%s/objects git %s' %(self.repo_dir, cmd)
        if dir:
            cmd = 'cd %s && %s' % (dir, cmd)
            
        self.system (cmd, ignore_error=ignore_error)

    def git_pipe (self, cmd, ignore_error=False):
        return self.read_pipe ('GIT_OBJECT_DIRECTORY=%s/objects git %s' %(self.repo_dir, cmd))
        
    def download (self):
        "Fetch updates from internet"
        
        repo = self.repo_dir
        source = self.source
        
        if not os.path.isdir (self.repo_dir):
            self.git ('--git-dir %(repo)s clone --bare -n %(source)s %(repo)s' % locals ())
            return

        if self.revision:
            contents = self.git_pipe ('--git-dir %(repo)s ls-tree %(revision)s' % locals (),
                                      ignore_error=True)

            if contents:
                return
            
            self.git ('--git-dir %(repo)s http-fetch -v -c %(revision)s' % locals ())

        refs = '%s:%s' % (self.branch, self.branch)
        
        self.git ('--git-dir %(repo)s fetch --update-head-ok %(source)s %(refs)s ' % locals ())
        self.checksums = {}

    def set_current_branch (self, branch):
        open (self.repo_dir + '/HEAD', 'w').write ('ref: refs/heads/%s\n' % branch)
        
    def get_checksum (self):
        
        branch = self.branch
        if self.checksums.has_key (branch):
            return self.checksums[branch]

        repo_dir = self.repo_dir
        if os.path.isdir (repo_dir):
            cs = self.git_pipe ('--git-dir %(repo_dir)s describe --abbrev=24 %(branch)s' % locals ())
            cs = cs.strip ()
            self.checksums[branch] = cs
            return cs
        else:
            return 'invalid'

    def all_files (self):
        branch = self.branch
        str = self.git_pipe ('ls-tree --name-only -r %(branch)s' % locals ())
        return str.split ('\n')

    def copy_to_working_dir (self, destdir):
        "Populate (preferably update) DESTDIR with sources of specified version/branch"

        repo_dir = self.repo_dir
        branch = self.branch

        if not os.path.isdir (destdir):
            self.system ('mkdir -p ' + destdir)

        if os.path.isdir (destdir + '/.git'):
            self.git ('pull %(repo_dir)s' % locals (), dir=destdir)
        else:
            self.git ('init-db', dir=destdir)

        if not revision:
            revision = open ('%(repo_dir)s/refs/heads/%(branch)s' % locals ()).read ()

        if not branch:
            branch = 'gub_build'
            
        open ('%(destdir)s/.git/refs/heads/%(branch)s' % locals (), 'w').write (revision)
        self.git ('checkout %(branch)s' % locals (), dir=destdir) 

class CVSRepository(Repository):
    cvs_entries_line = re.compile ("^/([^/]*)/([^/]*)/([^/]*)/([^/]*)/")
    #tag_dateformat = '%Y/%m/%d %H:%M:%S'

    def __init__ (self, dir, module):
        Repository.__init__ (self)
        self.repo_dir = dir
        self.module = module
        self.checksums = {}
        if not os.path.isdir (dir):
            self.system ('mkdir -p %s' % dir)
        
    def get_branch_version (self, branch):
        if self.checksums.has_key (branch):
            return self.checksums[branch]
        
        file = '%s/%s/.vc-checksum' % (self.repo_dir, branch)

        if os.path.exists (file):
            cs = open (file).read ()
            self.checksums[branch] = cs
            return cs
        else:
            return '0'

    def read_cvs_entries (self, dir):
        checksum = md5.md5()

        latest_stamp = 0
        for d in self.cvs_dirs (dir):
            for e in self.cvs_entries (d):
                (name, version, date, dontknow) = e
                checksum.update (name + ':' + version)

                if date == 'Result of merge':
                    raise Exception ("repository has been altered")
                
                stamp = time.mktime (time.strptime (date))
                latest_stamp = max (stamp, latest_stamp)

        version_checksum = checksum.hexdigest ()
        time_stamp = latest_stamp

        return (version_checksum, time_stamp)
    
    def update_workdir (self, destdir, branch=None, revision=None):
        
        suffix = branch
        if revision:
            suffix = revision
        dir = self.repo_dir  +'/' + suffix        


        ## TODO: can we get deletes from vc?
        self.system ('rsync -av --delete --exclude CVS %(dir)s/ %(destdir)s' % locals ())
        
    def download (self, source, branch=None, revision=None):
        suffix = branch
        rev_opt = '-r ' + branch
        if revision:
            suffix = revision
            rev_opt = '-r ' + revision
            
        dir = self.repo_dir  +'/' + suffix        

        lock_dir = locker.Locker (dir + '.lock')
        module = self.module
        cmd = ''
        if os.path.isdir (dir + '/CVS'):
            cmd += 'cd %(dir)s && cvs -q up -dAP %(rev_opt)s' % locals()
        else:
            repo_dir = self.repo_dir
            cmd += 'cd %(repo_dir)s/ && cvs -d %(source)s -q co -d %(suffix)s %(rev_opt)s %(module)s''' % locals ()

        self.system (cmd)

        (cs, stamp) = self.read_cvs_entries (dir)

        open (dir + '/.vc-checksum', 'w').write (cs)
        open (dir + '/.vc-timestamp', 'w').write ('%d' % stamp)
        
    def cvs_dirs (self, branch_dir):
        retval =  []
        for (base, dirs, files) in os.walk (branch_dir):
            retval += [os.path.join (base, d) for d in dirs
                       if d == 'CVS']
            
        return retval

    def cvs_entries (self, dir):
        entries_str =  open (os.path.join (dir, 'Entries')).read ()

        entries = []
        for e in entries_str.split ('\n'):
            m = self.cvs_entries_line.match (e)
            if m:
                entries.append (tuple (m.groups ()))
        return entries
        
    def all_cvs_entries (self, dir):
        ds = self.cvs_dirs (dir)
        es = []
        for d in ds:
            
            ## strip CVS/
            basedir = os.path.split (d)[0]
            for e in self.cvs_entries (d):
                filename = os.path.join (basedir, e[0])
                filename = filename.replace (self.repo_dir + '/', '')

                es.append ((filename,) + e[1:])
            

        return es

    def all_files (self, branch):
        entries = self.all_cvs_entries (self.repo_dir + '/' + branch)
        return [e[0] for e in entries]
    
    
class SVNRepository (Repository):
    def __init__ (self, dir, branch, module, revision):
        Repository.__init__ (self)
        self.dir = dir + '.svn'
        self.branch = branch
        self.module = module
        self.revision = revision
        if not os.path.isdir (self.dir):
            self.system ('mkdir -p %(dir)s' % self.__dict__)
        
    def update_workdir (self, destdir):
        working = self._get_working_dir ()
        self._copy_working_dir (working, destdir)

    def download (self):
        working = self._get_working_dir ()
        if not os.path.isdir (working + '/.svn'):
            self._checkout (source, self.branch, self.module, self.revision)
        self._update (working, self.revision)

    def get_checksum (self):
        working = self._get_working_dir ()
        revno = self.read_pipe ('cd %(working)s && svn info' % locals ())
        return re.sub ('.*Revision: ([0-9]*).*', '\\1', revno)

    def _checkout (self, source, branch, module, revision):
        '''SVN checkout'''
        dir = self.dir
        rev_opt = '-r %(revision)s ' % locals ()
        cmd = 'cd %(dir)s && svn co %(rev_opt)s %(source)s/%(branch)s/%(module)s %(branch)s-%(revision)s''' % locals ()
        self.system (cmd)
        
    def _copy_working_dir (self, working, copy):
        self.system ('rsync -av --exclude .svn %(working)s/ %(copy)s'
                     % locals ())
        
    def _get_working_dir (self):
        revision = self.revision
        dir = self.dir
        branch = self.branch
        return '%(dir)s/%(branch)s-%(revision)s' % locals ()

    def _update (self, working, revision):
        '''SVN update'''
        rev_opt = '-r %(revision)s ' % locals ()
        cmd = 'cd %(working)s && svn up %(rev_opt)s' % locals ()
        self.system (cmd)
