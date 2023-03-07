import glob
import pathlib
import re
import repack
import unpackMame
import argparse


def camelCaseSplit(str):
    str = str[0].upper()+str[1:]
    return re.findall(r'[A-Z0-9](?:[a-z0-9]+|[A-Z0-9]*(?=[A-Z0-9]|$))', str)


def guessDiskName(str):
    return " ".join(camelCaseSplit(str)).upper()


exc = {"grandstand/musicCartridgeDemo": {"patcherLoc": 0x58F0, "fix_checksum": False}
       }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Batch conversion of bins to sf7')
    parser.add_argument("srcdir")
    parser.add_argument("outdir")
    args = parser.parse_args()

    for c, filename in enumerate(sorted(glob.glob(args.srcdir+"/**/*.bin",
                                                  recursive=True))):
        src = pathlib.Path(filename)
        id = src.parent.stem+"/"+src.stem

        opts = {"diskname": guessDiskName(src.stem), "verbose": False}
        if id in exc:
            opts.update(exc[id])

        parts = unpackMame.decomposeSavefile(src)
        outName = pathlib.Path(args.outdir)/(id+".sf7")
        outName.parent.mkdir(parents=True, exist_ok=True)
        print(f"{c:03d}: Making {opts['diskname']} from {id}")
        repack.makeFloppy("loader", parts, outName, **opts)
