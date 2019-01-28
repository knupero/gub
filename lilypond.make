# -*-Makefile-*-
.PHONY: all default distclean packages nsis rest print-success print-branches
.PHONY: clean realclean
.PHONY: test test-output test-clean
.PHONY: update-versions unlocked-update-versions
.PHONY: doc doc-clean doc-export unlocked-doc-clean unlocked-doc-export
.PHONY: dist-check unlocked-dist-check
.PHONY: lilypond-prep nongit-dirs
.PHONY: lilypond-upload

default: all
	$(info **** Default rule)

LILYPOND_BRANCH=master
BUILDSCRIPTS=scripts/build
#BUILDSCRIPTS=buildscripts
# LILYPOND_BRANCH=stable/2.10
LILYPOND_REPO_URL=git://git.sv.gnu.org/lilypond.git

ALL_PLATFORMS=linux-x86 darwin-ppc darwin-x86 mingw linux-64 debian debian-arm freebsd-64 freebsd-x86 debian-mipsel linux-ppc linux-mipsel
ALL_PLATFORMS += cygwin

PLATFORMS=linux-x86
PLATFORMS+=darwin-ppc darwin-x86
PLATFORMS+=mingw
PLATFORMS+=linux-64
PLATFORMS+=linux-ppc
# Works for me, uncommentme!
# PLATFORMS+=linux-mipsel
PLATFORMS+=freebsd-x86 freebsd-64
# Put cygwin last, because it is not a core lilypond platform. 
#PLATFORMS += cygwin

ifeq ($(LILYPOND_BRANCH),stable/2.10)
$(error backportme:\
0d9ce36... When LINK_GXX_STATICALLY=yes, use CC (ie, [*-*-]gcc) for linking.  Fixes --enable-static-c++.\
841ee1b... PYTHON-CONFIG: also strip -m* and =.  Thanks Werner!\
f9e5179... Append /../lib to default rpath.\
fc158e0... Add --enable-rpath feature, defaulting to $ORIGIN/../lib. Default off.\
23e401a... Clean-out some junk flags from python-config.  Fixes stray g++ warning ****s.\
)
endif

# derived info
LILYPOND_SOURCE_URL=$(LILYPOND_REPO_URL)?branch=$(LILYPOND_BRANCH)
LILYPOND_DIRRED_BRANCH=$(shell $(PYTHON) gub/repository.py --branch-dir '$(LILYPOND_SOURCE_URL)')
LILYPOND_FLATTENED_BRANCH=$(shell $(PYTHON) gub/repository.py --full-branch-name '$(LILYPOND_SOURCE_URL)')
BUILD_PACKAGE='$(LILYPOND_SOURCE_URL)'

# these keep the git branch name when making packages
INSTALL_PACKAGE=$(subst lilypond,lilypond-installer,$(BUILD_PACKAGE))
DOC_PACKAGE=$(subst lilypond,lilypond-doc,$(BUILD_PACKAGE))
TEST_PACKAGE=$(subst lilypond,lilypond-test,$(BUILD_PACKAGE))

MAKE += -f lilypond.make

# FIXME: this is duplicated and must match actual info in guile.py

GUB_OPTIONS =

GPKG_OPTIONS =\
 $(if $(GUILE_LOCAL_BRANCH), --branch=guile=$(GUILE_LOCAL_BRANCH),)\
 --branch=lilypond=$(LILYPOND_BRANCH)

INSTALLER_BUILDER_OPTIONS =\
 $(if $(GUILE_LOCAL_BRANCH), --branch=guile=$(GUILE_LOCAL_BRANCH),)\
 --branch=lilypond=$(LILYPOND_FLATTENED_BRANCH)

include gub.make

NATIVE_TARGET_DIR=$(CWD)/target/$(BUILD_PLATFORM)
TOOLS_BIN_DIR=$(CWD)/target/tools/root/usr/bin/

SET_TOOLS_PATH=PATH=$(CWD)/target/tools/root/usr/bin:$(PATH)

LILYPOND_VERSIONS = versiondb/lilypond.versions

include compilers.make

################

unlocked-update-versions:
	$(info **** **** unlocked-update-versions rule)
	$(PYTHON) gub/versiondb.py --version-db=$(LILYPOND_VERSIONS) --download --platforms="$(PLATFORMS)"

ifneq ($(findstring cygwin,$(PLATFORMS)),)
# this is downloading the same info 5 times. Can we do this more efficiently?
	$(PYTHON) gub/versiondb.py --no-sources --version-db=versiondb/freetype2.versions --download  --platforms="cygwin"
	$(PYTHON) gub/versiondb.py --no-sources --version-db=versiondb/fontconfig.versions --download  --platforms="cygwin"
	$(PYTHON) gub/versiondb.py --no-sources --version-db=versiondb/guile.versions --download --platforms="cygwin"
	$(PYTHON) gub/versiondb.py --no-sources --version-db=versiondb/libtool.versions --download --platforms="cygwin"
	$(PYTHON) gub/versiondb.py --no-sources --version-db=versiondb/noweb.versions --download --platforms="cygwin"
endif

download-cygwin:
	$(info **** download-cygwin rule)
	$(MAKE) downloads/genini
	rm -f target/*/status/lilypond*
	rm -f log/lilypond-$(LILYPOND_VERSION)*.*.test.pdf

## should be last, to incorporate changed VERSION file.
	$(MAKE) update-versions

## same command as  lilypond.versions:
update-versions:
	$(info **** update-versions rule)
	$(PYTHON) gub/with-lock.py --skip $(LILYPOND_VERSIONS).lock $(MAKE) unlocked-update-versions

## same command as  update-versions:
$(LILYPOND_VERSIONS):
	$(info **** LILYPOND_VERSIONS rule)
	$(PYTHON) gub/with-lock.py --skip $(LILYPOND_VERSIONS).lock $(MAKE) unlocked-update-versions

regtests/ignore:
	$(info **** regtests/ignore rule)
	@echo 
	@echo 
	@echo "******************************************************"
	@echo "CHECK: regression tests tarball  (i.e. something like"
	@echo "\t lilypond-2.13.4-1.test-output.tar.bz2"
	@echo ") should be placed in regtests/"
	@echo
	@echo "When you have done this, disable this check by doing:"
	@echo "\t touch regtests/ignore"
	@echo "******************************************************"
	@echo 
	@echo
	exit 1

nongit-dirs:
	$(info **** nongit-dirs rule)
	mkdir -p versiondb regtests uploads

lilypond-prep: nongit-dirs $(LILYPOND_VERSIONS) regtests/ignore
	$(info **** lilypond-prep rule)

all: lilypond-prep packages rest
	$(info **** all rule)

ifeq ($(findstring mingw, $(PLATFORMS)),mingw)
rest: nsis
endif

rest: lilypond-installers test doc doc-export print-success
	$(info **** rest rule)

test: dist-check test-output test-export
	$(info **** test rule)

doc:
	$(info **** doc rule)
	$(call INVOKE_GUB,$(BUILD_PLATFORM)) $(DOC_PACKAGE)

test-output:
	$(info **** test-output rule)
	$(call INVOKE_GUB,$(BUILD_PLATFORM)) $(TEST_PACKAGE)

print-success:
	$(info **** print-success rule)
	$(PYTHON) test-lily/upload.py --branch=$(LILYPOND_BRANCH) --url $(LILYPOND_REPO_URL)
	@echo ""
	@echo "To upload, run:"
	@echo
	@echo "    make lilypond-upload LILYPOND_BRANCH=$(LILYPOND_BRANCH) LILYPOND_REPO_URL=$(LILYPOND_REPO_URL)"
	@echo

docball = uploads/lilypond-$(DIST_VERSION)-$(DOC_BUILDNUMBER).documentation.tar.bz2
webball = uploads/lilypond-$(DIST_VERSION)-$(DOC_BUILDNUMBER).webdoc.tar.bz2

$(docball):
	$(info **** docball rule)
#keep this target and just move/repackage lilypond-doc.gup,
#easier to handle versions.db?
	$(MAKE) doc

upload-setup-ini:
	$(info **** upload-setup-ini rule)
	cd uploads/cygwin && ../../downloads/genini $$(find release -mindepth 1 -maxdepth 2 -type d) > setup.ini

downloads/genini:
	$(info **** downloads/genini rule)
	wget --output-document $@ 'http://cygwin.com/cgi-bin/cvsweb.cgi/~checkout~/genini/genini?rev=1.2&content-type=text/plain&cvsroot=cygwin-apps&only_with_tag=HEAD'
	chmod +x $@

lily-clean:
	$(info **** lily-clean rule)
	rm -rf target/$(BUILD_PLATFORM)/*/lilypond-$(LILYPOND_FLATTENED_BRANCH)*

lily-doc-clean:	doc-clean
	$(info **** lily-doc-clean rule)

clean:
	$(info **** clean rule)
	rm -rf $(foreach p, $(PLATFORMS), target/*$(p)* )

realclean:
	$(info **** realclean rule)
	rm -rf $(foreach p, $(PLATFORMS), uploads/$(p)/* uploads/$(p)-cross/* target/*$(p)* )

################################################################
# compilers and tools

tools := $(shell PATH=$(PATH) $(GUB) --show-dependencies $(foreach p, $(PLATFORMS), $(p)::lilypond $(p)::lilypond-doc $(p)::lilypond-installer) 2>&1 | grep ^dependencies | tr ' ' '\n' | grep 'tools::')

ptools:
	$(info **** ptools rule)
	$(GUB) --show-dependencies $(foreach p, $(PLATFORMS), $(p)::lilypond $(p)::lilypond-doc $(p)::lilypond-installer) 2>&1 | grep ^dependencies | tr ' ' '\n' | grep 'tools::'

nsis:
	$(info **** nsis rule)
	$(GUB) tools::nsis

################################################################
# docs

NATIVE_ROOT=$(NATIVE_TARGET_DIR)/installer/lilypond-$(LILYPOND_FLATTENED_BRANCH)
NATIVE_DOC_ROOT=$(NATIVE_TARGET_DIR)/installer/lilypond-$(LILYPOND_FLATTENED_BRANCH)-doc
DOC_LOCK=$(NATIVE_ROOT).lock
TEST_LOCK=$(NATIVE_ROOT).lock

NATIVE_LILY_BUILD=$(NATIVE_TARGET_DIR)/build/lilypond-$(LILYPOND_FLATTENED_BRANCH)
NATIVE_LILY_SRC=$(NATIVE_TARGET_DIR)/src/lilypond-$(LILYPOND_FLATTENED_BRANCH)
# URG: try to guess at what repository will do.  should ask
# repository.read_file(), I guess.
LILYPOND_REPO_DIR=downloads/lilypond
LILYPOND_REPO_BRANCH_DIR=$(LILYPOND_REPO_DIR)/$(dir $(LILYPOND_DIRRED_BRANCH))
NATIVE_BUILD_COMMITTISH=$(shell cat $(LILYPOND_REPO_DIR)/git/refs/heads/$(LILYPOND_DIRRED_BRANCH))

print:
	$(info **** print rule)
	@echo LILYPOND_DIRRED_BRANCH $(LILYPOND_DIRRED_BRANCH)
	@echo LILYPOND_FLATTENED_BRANCH  $(LILYPOND_FLATTENED_BRANCH)
	@echo BUILD_PACKAGE $(BUILD_PACKAGE)
	@echo DOC_PACKAGE $(DOC_PACKAGE)
	@echo TEST_PACKAGE $(TEST_PACKAGE)
	@echo NATIVE_BUILD_COMMITTISH $(NATIVE_BUILD_COMMITTISH)
	@echo LILYPOND_REPO_BRANCH_DIR $(LILYPOND_REPO_BRANCH_DIR)
	@echo LILYPOND_REPO_DIR $(LILYPOND_REPO_DIR)

DIST_VERSION=$(shell cat $(NATIVE_LILY_BUILD)/out/VERSION)
DOC_BUILDNUMBER=$(shell $(PYTHON) gub/versiondb.py --platforms=$(PLATFORMS) --build-for=$(DIST_VERSION))

SIGNATURE_FUNCTION=uploads/signatures/$(1).$(NATIVE_BUILD_COMMITTISH)

doc-clean:
	$(info **** doc-clean rule)
	$(PYTHON) gub/with-lock.py --skip $(DOC_LOCK) $(MAKE) unlocked-doc-clean

test-clean:
	$(info **** test-clean rule)
	$(PYTHON) gub/with-lock.py --skip $(TEST_LOCK) $(MAKE) unlocked-test-clean

unlocked-doc-clean:
	$(info **** unlocked-doc-clean rule)
	make -C $(NATIVE_TARGET_DIR)/build/lilypond-$(LILYPOND_FLATTENED_BRANCH) \
		DOCUMENTATION=yes doc-clean
	rm -rf $(NATIVE_TARGET_DIR)/build/lilypond-$(LILYPOND_FLATTENED_BRANCH)/out/lybook-db
	rm -f $(call SIGNATURE_FUNCTION,cached-doc-build)
	rm -f $(call SIGNATURE_FUNCTION,cached-doc-export)

unlocked-test-clean:
	$(info **** unlocked-test-clean rule)
	make -C $(NATIVE_TARGET_DIR)/build/lilypond-$(LILYPOND_FLATTENED_BRANCH) \
		DOCUMENTATION=yes test-clean
	rm -f $(call SIGNATURE_FUNCTION,cached-test-output)

cached-dist-check cached-doc-export cached-test-export:
	$(info **** cached-dist-check cached-doc-export cached-test-export rule)
	-mkdir -p uploads/signatures
	if test ! -f  $(call SIGNATURE_FUNCTION,$@) ; then \
		$(SET_TOOLS_PATH) \
		$(MAKE) $(subst cached,unlocked,$@) \
		&& touch $(call SIGNATURE_FUNCTION,$@) ; fi

unlocked-doc-export:
	$(info **** unlocked-doc-export rule)
	PYTHONPATH=$(NATIVE_LILY_BUILD)/python/out \
	$(PYTHON) test-lily/rsync-lily-doc.py --recreate \
		--version-file=$(NATIVE_LILY_BUILD)/out/VERSION \
		--output-distance=$(NATIVE_LILY_SRC)/$(BUILDSCRIPTS)/output-distance.py $(NATIVE_LILY_BUILD)/out-www/online-root
	$(PYTHON) test-lily/rsync-lily-doc.py --recreate \
		--version-file=$(NATIVE_LILY_BUILD)/out/VERSION \
		--unpack-dir=uploads/localdoc/ \
		--output-distance=$(NATIVE_LILY_SRC)/$(BUILDSCRIPTS)/output-distance.py $(NATIVE_LILY_BUILD)/out-www/offline-root

unlocked-test-export:
	$(info **** unlocked-test-export rule)
	mkdir -p uploads/webtest
	PYTHONPATH=$(NATIVE_LILY_BUILD)/python/out \
	$(SET_TOOLS_PATH) \
		$(PYTHON) test-lily/rsync-test.py \
		--version-file=$(NATIVE_LILY_BUILD)/out/VERSION \
		--output-distance=$(NATIVE_LILY_SRC)/$(BUILDSCRIPTS)/output-distance.py \
		--test-dir=uploads/webtest \
		--gub-target-dir=$(NATIVE_TARGET_DIR)

doc-export:
	$(info **** doc-export rule)
	$(SET_TOOLS_PATH) \
		$(PYTHON) gub/with-lock.py --skip $(DOC_LOCK) $(MAKE) cached-doc-export

test-export:
	$(info **** test-export rule)
	$(SET_TOOLS_PATH) \
		$(PYTHON) gub/with-lock.py --skip $(DOC_LOCK) $(MAKE) cached-test-export

unlocked-dist-check:
	$(info **** unlocked-dist-check rule)
	$(SET_TOOLS_PATH) \
		$(PYTHON) test-lily/dist-check.py\
		--branch=$(LILYPOND_BRANCH) \
		--url=$(LILYPOND_REPO_URL) \
		--repository=$(LILYPOND_REPO_DIR) $(NATIVE_LILY_BUILD)
	cp $(NATIVE_LILY_BUILD)/out/lilypond-$(DIST_VERSION).tar.gz uploads

dist-check:
	$(info **** dist-check rule)
	$(SET_TOOLS_PATH) \
		$(PYTHON) gub/with-lock.py --skip $(NATIVE_LILY_BUILD).lock \
		$(MAKE) cached-dist-check

print-branches:
	$(info **** print-branches rule)
	@echo "--branch=guile=$(GUILE_FLATTENED_BRANCH)"
	@echo "--branch=lilypond=$(LILYPOND_FLATTENED_BRANCH)"
	@echo "--branch=denemo=$(DENEMO_FLATTENED_BRANCH)"

lilypond-upload:
	$(info **** lilypond-upload rule)
	$(PYTHON) test-lily/upload.py --branch=$(LILYPOND_BRANCH) --url $(LILYPOND_REPO_URL) --execute
	mv uploads/lilypond-*.test-output.tar.bz2 regtests/

