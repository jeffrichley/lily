@REM Minimal makefile for Sphinx documentation
@REM

@REM You can set these variables from the command line, and also
@REM from the environment for the first two.
set SPHINXOPTS=
set SPHINXBUILD=sphinx-build
set SOURCEDIR=source
set BUILDDIR=build

@REM Put it first so that "make" without argument is like "make help".
help:
	%SPHINXBUILD% -M help "%SOURCEDIR%" "%BUILDDIR%" %SPHINXOPTS% %O%

.PHONY: help Makefile

@REM Catch-all target: route all unknown targets to Sphinx using the new
@REM "make mode" option.  %O% is meant as a shortcut for %SPHINXOPTS%.
%: Makefile
	%SPHINXBUILD% -M %* "%SOURCEDIR%" "%BUILDDIR%" %SPHINXOPTS% %O%
