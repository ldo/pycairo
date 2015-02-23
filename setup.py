#+
# Distutils script to build and install Pycairo. To avoid ending
# up with files in this directory belonging to root instead of
# the current user, do the build/install in two steps. First, as
# an ordinary user:
#
#     python3 setup.py build
#
# then:
#
#    sudo python3 setup.py install --skip-build
#
# To get rid of build products afterwards, do
#
#     python3 setup.py clean --all
#-

import sys
import os
import subprocess
import distutils.core as dic
from distutils.command.build import \
    build as std_build
from distutils.command.clean import \
    clean as std_clean

pycairo_version        = '1.10.1'
cairo_version_required = '1.10.2'
python_version_required = (3,0)
pkgconfig_file = 'py3cairo.pc'
config_file = 'src/config.h'
module_constants_file = "src/cairomodule_constants.h"

class my_build(std_build) :
    "customization of build to generate additional files."

    def run(self) :
        create_module_constants_file()
        createConfigFile(config_file)
        super().run()
        createPcFile(pkgconfig_file)
    #end run

#end my_build

class my_clean(std_clean) :
    "customization of clean to remove additional files and directories that I generate."

    def run(self) :
        super().run()
        for \
            dir \
        in \
            (
                "doc/_build",
            ) \
        :
            if os.path.isdir(dir) :
                for root, subdirs, subfiles in os.walk(dir, topdown = False) :
                    for item in subfiles :
                        os.unlink(os.path.join(root, item))
                    #end for
                    for item in subdirs :
                        os.rmdir(os.path.join(root, item))
                    #end for
                #end for
                os.rmdir(dir)
            #end if
        #end for
        for \
            item \
        in \
            (
                pkgconfig_file,
                config_file,
                module_constants_file,
            ) \
        :
            try :
                os.unlink(item)
            except OSError :
                pass # assume ENOENT
            #end try
        #end for
    #end run

#end my_clean


def call(command):
  pipe = subprocess.Popen(command, shell=True,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
  pipe.wait()
  return pipe

def pkg_config_version_check(pkg, version):
  check = '%s >= %s' % (pkg, version)
  pipe = call("pkg-config --print-errors --exists '%s'" % (check,))
  if pipe.returncode == 0:
    print(check, ' Successful')
  else:
    print(check, ' Failed')
    raise SystemExit(pipe.stderr.read().decode())

def pkg_config_parse(opt, pkg):
  check = "pkg-config %s %s" % (opt, pkg)
  pipe = call("pkg-config %s %s" % (opt, pkg))
  if pipe.returncode != 0:
    print(check, ' Failed')
    raise SystemExit(pipe.stderr.read().decode())

  output = pipe.stdout.read()
  output = output.decode() # get the str
  opt = opt[-2:]
  return [x.lstrip(opt) for x in output.split()]


def createPcFile(PcFile):
  print('creating %s' % PcFile)
  with open(PcFile, 'w') as fo:
    fo.write ("""\
prefix=%s

Name: Pycairo
Description: Python 3 bindings for cairo
Version: %s
Requires: cairo
Cflags: -I${prefix}/include/pycairo
Libs:
""" % (sys.prefix, pycairo_version)
            )

def createConfigFile(ConfigFile):
  print('creating %s' % ConfigFile)
  v = pycairo_version.split('.')

  with open(ConfigFile, 'w') as fo:
    fo.write ("""\
// Configuration header created by setup.py - do not edit
#ifndef _CONFIG_H
#define _CONFIG_H 1

#define PYCAIRO_VERSION_MAJOR %s
#define PYCAIRO_VERSION_MINOR %s
#define PYCAIRO_VERSION_MICRO %s
#define VERSION "%s"

#endif // _CONFIG_H
""" % (v[0], v[1], v[2], pycairo_version)
            )


if sys.version_info < python_version_required:
  raise SystemExit('Error: Python >= %s is required' %
                   (python_version_required,))

pkg_config_version_check ('cairo', cairo_version_required)
if sys.platform == 'win32':
  runtime_library_dirs = []
else:
  runtime_library_dirs = pkg_config_parse('--libs-only-L', 'cairo')

def create_module_constants_file() :
    "generates C source that wraps all the repetitive CAIRO_HAS_xxx constants."
    out = open(module_constants_file, "w")
    out.write("  /* constants */\n")
    for \
        name \
    in \
        (
            "ATSUI_FONT",
            "FT_FONT",
            "FC_FONT",
            "GLITZ_SURFACE",
            "IMAGE_SURFACE",
            "PDF_SURFACE",
            "PNG_FUNCTIONS",
            "PS_SURFACE",
            "RECORDING_SURFACE",
            "SVG_SURFACE",
            "USER_FONT",
            "QUARTZ_SURFACE",
            "WIN32_FONT",
            "WIN32_SURFACE",
            "XCB_SURFACE",
            "XLIB_SURFACE",
        ) \
    :
        out.write \
          (
                "#if CAIRO_HAS_%(name)s\n"
                "  PyModule_AddIntConstant(m, \"HAS_%(name)s\", 1);\n"
                "#else\n"
                "  PyModule_AddIntConstant(m, \"HAS_%(name)s\", 0);\n"
                "#endif\n"
            %
                {
                    "name" : name,
                }
          )
    #end for
    out.flush()
#end create_module_constants_file

cairo = dic.Extension(
  name = 'cairo._cairo',
  sources = ['src/cairomodule.c',
             'src/context.c',
             'src/font.c',
             'src/matrix.c',
             'src/path.c',
             'src/pattern.c',
             'src/region.c',
             'src/surface.c',
             ],
  include_dirs = pkg_config_parse('--cflags-only-I', 'cairo'),
  library_dirs = pkg_config_parse('--libs-only-L', 'cairo'),
  libraries    = pkg_config_parse('--libs-only-l', 'cairo'),
  runtime_library_dirs = runtime_library_dirs,
  )

dic.setup \
  (
    cmdclass =
        {
            "build" : my_build,
            "clean" : my_clean,
        },
    name = "pycairo",
    version = pycairo_version,
    description = "python interface for cairo",
    ext_modules = [cairo],
    package_dir = {"cairo" : "src"},
    packages = ["cairo"],
    data_files =
        [
          ('include/pycairo', ['src/py3cairo.h']),
          ('lib/pkgconfig', [pkgconfig_file]),
        ],
  )
