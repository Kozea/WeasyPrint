"""

    build_wheel.py
    ==============

    Running this scripts builds wheel by collecting necessary
    binaries for Windows. 

    This runs of Python 3.6+.

    Deps: see requirements.txt.

    :copyright: Naveen M K <naveen@syrusdark.website>
    :license: BSD, See LICENSE for details.

"""
import logging
import re
import argparse
import shutil
import struct
import subprocess
import tempfile
import typing
import urllib.request
import zipfile
from pathlib import Path

from build import ProjectBuilder
from build.env import IsolatedEnvBuilder
from wheel.cli.pack import pack as wheelpack
from wheel.cli.unpack import unpack as wheelunpack

try:
    from wheel.bdist_wheel import get_platform
except ImportError:
    # old version of wheel
    from wheel.pep425tags import get_platform


logger = logging.getLogger(__name__)
PANGO_VERSION = "1.48.2"
BUILD_URL = "https://github.com/naveen521kk/pango-build/releases/download/v{version}/pango-build-win{arch}.zip"


def get_wheel_tag() -> typing.Tuple[str, str, str]:
    """get_wheel_tag, the tag which needs to put into the wheel.
    This will return a tag which can be used across any python
    with no ABI specification.

    :return: The wheels tag
    :rtype: typing.Tuple[str, str, str]
    """
    plat_name = get_platform(None).replace("-", "_")
    # python3 no abi, platform
    return ("py3", "none", plat_name)


def get_arch() -> int:
    """get_arch of the python this script is running

    :return: Either 32 or 64 based of the python it is running.
    :rtype: int
    """
    if (struct.calcsize("P") * 8) == 32:
        return "32"
    else:
        return "64"


def download_file(url: str, file: typing.Union[Path, str]) -> None:
    """download_file download a file to the specfied location.

    :param url: The URL to download from.
    :type url: str
    :param file: The file to save.
    :type file: typing.Union[Path, str]
    """
    logger.info("Downloading %s to %s...", url, file)
    with urllib.request.urlopen(url) as response, open(file, "wb") as f:
        shutil.copyfileobj(response, f)
    logger.info("Download Complete.")


def download_binaries(arch: int, download_directory: typing.Union[Path, str]) -> None:
    """download_binaries for pango from ``BUILD_URL`` for the particular
    ``arch`` and saves it to download_directory. It also cleans
    ``download_directory`` if it is not empty.

    :param arch: The arch to download. Allowed value are 32 and 64.
    :type arch: int
    :param download_directory: The place to save the downloaded files after
                extracting.
    :type download_directory: Path
    """
    # check if download_directory is Path else convert it
    if not isinstance(download_directory, Path):
        download_directory = Path(download_directory)

    # first check if download_directory exists
    # if it exists clean it
    # else create that directory
    if download_directory.exists():
        shutil.rmtree(download_directory)
    download_directory.mkdir(exist_ok=True)

    download_url = BUILD_URL.format(version=PANGO_VERSION, arch=arch)
    with tempfile.TemporaryDirectory() as tempdir:
        temp = Path(tempdir, "temp.zip")
        download_file(download_url, temp)
        logging.info("Extracting %s", temp)
        with zipfile.ZipFile(temp) as zip:
            zip.extractall(download_directory)
        logger.info("Completed Extracting. Saved to %s", download_directory)


def get_git_toplevel(path: typing.Union[str, Path] = ".") -> Path:
    """get_git_toplevel gets the top level of the git repo
    so that it can be passed to python-build to create wheels
    initially which later needs to be edited.

    Copied from https://github.com/pypa/setuptools_scm/blob/master/src/setuptools_scm/file_finder_git.py#L12-L42
    and modified to use pathlib.

    :param path: The current directory or directory from which
    to find toplevel.
    :type path: typing.Union[str, Path]
    :raises Exception: When ``git`` isn't found.
    :return: The toplevel directory in git.
    :rtype: Path
    """
    try:
        cwd = str(Path(path or ".").absolute())
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-prefix"],
            cwd=cwd,
            universal_newlines=True,
            stderr=subprocess.DEVNULL,
        )
        out = out.strip()[:-1]  # remove the trailing pathsep
        if not out:
            out = cwd
        else:
            # Here, ``out`` is a relative path to root of git.
            # ``cwd`` is absolute path to current working directory.
            # the below method removes the length of ``out`` from
            # ``cwd``, which gives the git toplevel
            assert cwd.replace("\\", "/").endswith(out)
            # In windows cwd contains ``\`` which should be replaced by ``/``
            # for this assertion to work. Length of string isn't changed by replace
            # ``\\`` is just and escape for `\`
            out = cwd[: -len(out)]
        return Path(out.strip())
    except (subprocess.CalledProcessError, OSError):
        raise Exception("Git is Required to Build Wheels.")


def build_normal_wheel(
    output_directory: typing.Union[str, Path], distribution: str = "wheel"
) -> Path:
    """build_normal_wheel, it builds normal wheels which would be
    usually created using Python Build. This wheels is then
    patched so that it includes those DLL files.

    :param output_directory: The directory to save the file.
    :type output_directory: typing.Union[str, Path]
    :param distribution: Build wheel or source, defaults to "wheel"
    :type distribution: str, optional
    :return: The location of the wheel.
    :rtype: Path
    """
    logger.info("Building Normal Wheel")
    rootdir = get_git_toplevel(Path(__file__).parent)
    logger.info("Found root directory as %s", rootdir)
    with IsolatedEnvBuilder() as env:
        builder = ProjectBuilder(srcdir=rootdir)
        builder.python_executable = env.executable
        builder.scripts_dir = env.scripts_dir
        # first install the build dependencies
        env.install(builder.build_dependencies)
        # then install other dependencies
        env.install(builder.get_dependencies(distribution))
        builder.build(distribution, str(output_directory))
    logger.info("Build completed without any error.")
    return [i for i in Path(output_directory).glob("*.whl")][0]


def patch_wheel(
    orig_wheel: typing.Union[str, Path],
    bin_dir: typing.Union[str, Path],
    final_wheel_dir: typing.Union[str, Path],
) -> Path:
    """patch_wheel, patches the wheel generated by build
    so that it includes binaries and also is appropriately
    tagged.

    :param orig_wheel: The location of original wheel.
    :type orig_wheel: typing.Union[str, Path]
    :param bin_dir: The location of the DLL files
    :type bin_dir: typing.Union[str, Path]
    :param final_wheel_dir: The location to save the wheel finally
    :type final_wheel_dir: typing.Union[str, Path]
    :return: The wheel's location.
    :rtype: Path
    """
    if not isinstance(orig_wheel, Path):
        orig_wheel = Path(orig_wheel)

    if not isinstance(bin_dir, Path):
        bin_dir = Path(bin_dir)
    if not isinstance(final_wheel_dir, Path):
        final_wheel_dir = Path(final_wheel_dir)
    if not final_wheel_dir.is_dir():
        final_wheel_dir.mkdir()
    package_name_pypi = orig_wheel.stem.split("-")[0]
    version_number = orig_wheel.stem.split("-")[1]
    logger.info("Found package_name_pypi: %s", package_name_pypi)
    logger.info("Found version_number: %s", version_number)

    # first move to a temporary directory
    with tempfile.TemporaryDirectory() as tempdir:
        logger.info("Using temporary directory %s", tempdir)

        # now unpack the wheel here
        logger.info("Unpacking Original Wheel...")
        wheelunpack(orig_wheel, tempdir)

        # it should be unpacked to tempdir/{package_name}-{version_number}
        unpack_location = Path(tempdir, f"{package_name_pypi}-{version_number}")
        # first get the top module name. without that it should be
        # impossible for me to know which directory to put the
        # dll's into. Assume, there should be only one toplevel directory,
        # in that case there should two directories in `unpack_location`, one
        # with `{package_name_pypi}-{version_number}.dist-info` and other with
        # module name.
        possible_module_names = [
            i
            for i in unpack_location.iterdir()
            if i.is_dir() and not i.name.endswith("dist-info")
        ]
        assert len(possible_module_names) == 1, "Can't find unique module name."
        module_path = possible_module_names[0]
        logger.info("Found module_name: %s", module_path)

        # now add each of the `.dll` file in `bin_dir` to
        # `.libs` folder inside of unpacked directory of wheel.
        libs_folder = Path(module_path, ".libs")
        libs_folder.mkdir(exist_ok=True)
        logger.info("Libs Folder: %s", libs_folder)

        # start iterating and copying one by one.
        for local_path in bin_dir.glob("*.dll"):
            logger.info("Copying '%s' to '%s'", local_path, libs_folder)
            shutil.copy(local_path, libs_folder)

        # now copy the distributor init file in place
        logger.info("Copying _distributor_init.py")
        distributor_file = Path(__file__).parent / "windows_distributor_init.py"
        with open(distributor_file) as f:
            with open(module_path / "_distributor_init.py", "w") as f1:
                f1.write(f.read())

        # now copy LICENSE.bin to libs folder
        license_file = Path(__file__).parent / "LICENSE.bin"
        shutil.copy(license_file, libs_folder)

        # Now copy the fontconfig specific files to `.libs/fonts`
        # It exists in two different places
        # one in `etc/fonts` and other in `share/fontconfig`
        # First, the things in `share/fontconfig/conf.avail` should be
        # copied to `etc/fonts/conf.avail and then copy the things in `etc/fonts`
        # to `.libs/fonts`
        ROOT_BIN_INSTALL_DIR = bin_dir.parent
        shutil.copytree(
            ROOT_BIN_INSTALL_DIR / "share/fontconfig/conf.avail",
            ROOT_BIN_INSTALL_DIR / "etc/fonts/conf.avail",
        )
        shutil.copytree(
            ROOT_BIN_INSTALL_DIR / "etc/fonts",
            libs_folder / "fonts"
        )
        # now patch fonts.conf in `.libs/fonts` which will
        # contain WINDOWSFONTDIR and needs to replaced with
        # <dir>WINDOWSFONTDIR</dir>. See 
        # https://gitlab.freedesktop.org/fontconfig/fontconfig/-/issues/276
        # remove this in future
        fonts_conf_location = libs_folder / "fonts" / "fonts.conf"
        with open(fonts_conf_location) as f:
            c = f.read()
        c = c.replace("WINDOWSFONTDIR","<dir>WINDOWSFONTDIR</dir>")
        with open(fonts_conf_location,'w') as f:
            f.write(c)

        # Now that things are in place it should be fine to repack
        # the wheel. But we should make in windows only that to
        # either 32 bit or 64 bit. For that, we should edit
        # `*.dist-info/WHEEL` file.
        # replace the `Tag:` with the one from `get_wheel_tag()`
        final_wheel_tag = "-".join(get_wheel_tag())
        logger.info("Final wheel tag: %s", final_wheel_tag)
        wheel_file = [
            i
            for i in unpack_location.iterdir()
            if i.is_dir() and i.name.endswith("dist-info")
        ][0] / "WHEEL"
        logger.info("Wheel File: %s", wheel_file)

        # Use Regex to do that
        replace_tag_regex = re.compile(
            r"(Tag:) (?P<python>[^-]*)-(?P<abi>[^-]*)-(?P<platform>[^-]*)"
        )

        def subs(match: re.Match):
            logger.info("Previous Tags: %s", match.groupdict())
            final_tag = f"Tag: {final_wheel_tag}"
            logger.info("Final Tag: %s", final_tag)
            return final_tag

        with open(wheel_file, "r") as f:
            content = f.read()
        with open(wheel_file, "w") as f:
            final = replace_tag_regex.sub(subs, content)
            f.write(final)
        logger.info("Wrote wheel file.")

        # everything is done now. Simply repack the wheel.
        logger.info("Packing Wheel...")
        wheelpack(str(unpack_location), str(final_wheel_dir), None)
    final_wheel_loc = [i for i in Path(final_wheel_dir).glob("*.whl")][0]
    logger.info("Wheels Ready at %s", final_wheel_loc)
    return final_wheel_loc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build Wheels for Weasyprint.",
    )
    parser.add_argument(
        "dest_dir",
        type=str,
        help="the directory where to create the repaired wheel",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    working_dir = Path(tempfile.mkdtemp())
    orig_wheels_dir = working_dir / "orig_wheels"
    bin_dir = working_dir / "bin"
    final_wheels = args.dest_dir

    arch = get_arch()
    logger.info("Found Python to be %s bit", arch)
    download_binaries(arch, working_dir)
    logger.info("Building Normal Wheels")
    orig_wheel = build_normal_wheel(orig_wheels_dir)

    logger.info("Patching Wheels")
    patch_wheel(orig_wheel, bin_dir, final_wheels)
