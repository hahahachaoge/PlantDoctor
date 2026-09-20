"""python-for-android NumPy recipe pinned to the fixed v2.3.3 release."""

import shutil
from os.path import join

from pythonforandroid.recipe import MesonRecipe, Recipe


class NumpyRecipe(MesonRecipe):
    version = "v2.3.3"
    url = "git+https://github.com/numpy/numpy"
    extra_build_args = ["-Csetup-args=-Dblas=none", "-Csetup-args=-Dlapack=none"]
    need_stl_shared = True
    min_ndk_api_support = 24

    def get_include(self, arch):
        return join(
            self.ctx.get_python_install_dir(arch.arch),
            "numpy/_core/include",
        )

    def get_recipe_meson_options(self, arch):
        options = super().get_recipe_meson_options(arch)
        options["properties"]["longdouble_format"] = (
            "IEEE_DOUBLE_LE"
            if arch.arch in ["armeabi-v7a", "x86"]
            else "IEEE_QUAD_LE"
        )
        return options

    def get_recipe_env(self, arch, **kwargs):
        env = super().get_recipe_env(arch, **kwargs)
        env["_PYTHON_HOST_PLATFORM"] = arch.command_prefix
        env["NPY_DISABLE_SVML"] = "1"
        env["TARGET_PYTHON_EXE"] = join(
            Recipe.get_recipe("python3", self.ctx).get_build_dir(arch.arch),
            "android-build",
            "python",
        )
        return env

    def get_hostrecipe_env(self, arch=None):
        env = super().get_hostrecipe_env(arch=arch)
        env["RANLIB"] = shutil.which("ranlib")
        return env


recipe = NumpyRecipe()
