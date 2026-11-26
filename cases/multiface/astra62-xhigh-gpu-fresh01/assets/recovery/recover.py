"""Optional refit from the three supplied PNG sequences; requires Linux/OpenCV."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Directory containing cameras.json and views/")
    parser.add_argument("work", type=Path, help="Directory for temporary compiled code and fitted surfaces")
    parser.add_argument("assets", type=Path, help="New or empty directory for recovered assets")
    a = parser.parse_args()
    inp, work, assets = [p.resolve() for p in (a.input, a.work, a.assets)]
    if not (inp/"views/I1/frames").is_dir():
        parser.error("Not a capture input directory")
    if assets.exists() and any(assets.iterdir()):
        parser.error("Output assets directory must be empty")
    if inp == work or inp in work.parents or inp in assets.parents:
        parser.error("Keep working and output directories outside the input directory")
    work.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    env = {**os.environ, "MF_INPUT":str(inp), "MF_WORK":str(work), "MF_ASSETS":str(assets),
           "OPENBLAS_NUM_THREADS":"1", "OMP_NUM_THREADS":"1", "PYTHONDONTWRITEBYTECODE":"1"}
    flags = subprocess.check_output(["pkg-config", "--cflags", "--libs", "opencv4"], text=True)
    subprocess.run(["g++", "-shared", "-fPIC", "-O3", str(here/"ops.cpp"), "-o",
                    str(work/"ops.so"), *shlex.split(flags)], check=True)
    def run(*cmd):
        subprocess.run([sys.executable, *cmd], cwd=here, env=env, check=True)
    run("-c", "from reconstruct import *; a=[image(i,0) for i in range(3)];"
        "np.save(S/'base.npy',fitprime(a,[signed(mask(im,i)) for i,im in enumerate(a)]))")
    run("cache.py", "all")
    run("cache.py", "consolidate")
    run("finish_cloth.py")
    for name in ("cameras.json", "speech.wav", "SOURCE.txt"):
        shutil.copyfile(inp/name, assets/name)
    with Image.open(inp/"views/I1/frames/040434.png") as im:
        im.crop((29,1661,251,1883)).save(assets/"diffuser.png")


if __name__ == "__main__":
    main()
