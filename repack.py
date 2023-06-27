#! /usr/bin/env python3
import numpy as np
import unpackMame
import sys
import scfloppy
import zlib
import argparse
import pathlib


def findSpaces(mem):
    space = []
    v = None
    cnt = 0
    # print("length", len(mem))

    for i in range(len(mem)):
        if mem[i] == v:
            cnt += 1
        else:
            if cnt > 0x10:
                space.append((cnt, i-cnt, v))
            v = mem[i]
            cnt = 1
    if cnt > 0x10:
        space.append((cnt, i+1-cnt, v))
    return space


def chunkRep(m):
    u = np.unique(list(m))
    if len(u) == 1:
        return f"{u[0]:02x} "
    else:
        return "xx "


def plotMap(mem):
    for i, a in enumerate(range(0, len(mem), 256)):
        if a % 0x1000 == 0:
            print(f"{a:04x}", end=" ")
        print(chunkRep(mem[a:a+256]), end="\n" if i % 16 == 15 else "")


def printSpace(mem):
    space = findSpaces(mem)
    ss = sorted(space)
    for (cnt, addr, v) in ss:
        print(f"{cnt} at {addr:04x}-{(addr+cnt):04x} = {v:02x}")


def printSpaceByAddr(mem):
    space = findSpaces(mem)
    byAddr = sorted([(addr, cnt, v) for (cnt, addr, v) in space])
    for (addr, cnt, v) in byAddr:
        print(f"{addr:04x}-{(addr+cnt):04x} ({cnt})= {v:02x}")


def readSymbols(fname):
    sym = {}
    with open(fname) as f:
        for line in f.readlines():
            if line.strip()[0] == ";":
                continue
            loc, label = line.split()
            nloc = [int(x, 16) for x in loc.split(":")]
            sym[label] = nloc
    return sym


def hexString(x):
    return [f"{v:02x}" for v in x]


def isSingleVal(m, v):
    u = np.unique(list(m))
    return len(u) == 1 and u == v


def getBigZeroSpace(mem):
    space = findSpaces(mem)
    ss = sorted(space, reverse=True)
    for (cnt, addr, v) in ss:
        # print(f"{cnt},{addr:04x},{v:02x}")
        if v == 0x00 and addr < 0xFC00:
            return addr
    return 0xC000


def le16(x):
    return [x & 0xFF, x >> 8]


def thisDir():
    return pathlib.Path(__file__).resolve().parent


def makeFloppy(loadername, parts, outname, diskname="SAVEDATA",
               patcherLoc=None, fix_checksum=True, verbose=True):

    with open(loadername+".bin", "rb") as f:
        loaderBinData = f.read()
        loaderData = bytearray(loaderBinData[:0x100])
        patcherData = bytearray(loaderBinData[0x100:])
    sym = readSymbols(loadername+".sym")

    ramData = bytearray(parts["mem"])
    vramData = bytearray(parts["vram"])

    patcherCodeStart = sym["patcherCode"][1]
    patcherCodeSize = sym["patcherCodeEnd"][1]-patcherCodeStart

    if patcherLoc is None:
        patcherLoc = patcherCodeStart

    def put(symbol, vals, offset=0):
        sp = sym[symbol]
        if sp[0] == 0:  # loader
            offset -= 0xFF00
            target = loaderData
        else:  # patcher
            target = ramData
            offset += patcherLoc-patcherCodeStart
        addr = sp[1]+offset
        target[addr:addr+len(vals)] = vals
        # print(f"put {hexString(vals)} at {start:04x}")

    if not isSingleVal(ramData[patcherLoc:
                               patcherLoc+patcherCodeSize],
                       0xFF):
        print("PATCHER CODE IS OVERWRITING STUFF")

    ramData[patcherLoc:patcherLoc +
            patcherCodeSize] = patcherData[:patcherCodeSize]

    put("jumpPatcher", le16(patcherLoc), 1)
    frontRegsLoc = sym["frontRegs"][1]+patcherLoc-patcherCodeStart
    put("loadFrontRegs", le16(frontRegsLoc), 1)

    FC00_SRC = getBigZeroSpace(parts["mem"])
    FC00_SIZE = 0x400

    if not isSingleVal(ramData[FC00_SRC:FC00_SRC + FC00_SIZE], 0x00):
        print(f"HIGH RAM IS OVERWRITING STUFF at {FC00_SRC:04x}-" +
              f"{FC00_SRC + FC00_SIZE:04x}")
        plotMap(parts["mem"])
        printSpaceByAddr(parts["mem"])

    ramData[FC00_SRC:FC00_SRC + FC00_SIZE] = parts["mem"][
        0xFC00:0xFC00+FC00_SIZE]

    def putCpuReg(loc, regNames, offset=0):
        cpuVals = [parts["cpu"][r] for r in regNames]
        vals = [b for reg in cpuVals for b in reg]
        put(loc, vals, offset)
    frontNames = ["AF", "BC", "DE", "HL"]
    shadowNames = ["AF2", "BC2", "DE2", "HL2", "IX", "IY", ]
    putCpuReg("frontRegs", frontNames)
    putCpuReg("shadowRegs", shadowNames)
    putCpuReg("setSp", ["SP"], 1)
    putCpuReg("setPc", ["PC"], 1)

    isIntEnabled = parts["cpu"]["IFF2"]
    intOp = [0xFB] if isIntEnabled else [0xF3]
    put("setInterrupt", intOp)

    for i in range(8):
        val = parts["vregs"][i]
        put("vdpRegCmds", [val], 2*i)

    psgCmds = []

    # LCCTDDDD

    for i in range(3):
        tone = parts["psg"]["tone"][i]
        # print(f"tone[{i}]={tone:04x}")
        psgCmds.append(0b1000_0000 | (i << 5) | (tone & 0x0F))
        psgCmds.append(0b0000_0000 | ((tone >> 4) & 0x3F))
    noise = parts["psg"]["tone"][3]
    psgCmds.append(0b1000_0000 | (3 << 5) | (noise & 0x0F))
    for i in range(4):
        psgCmds.append(0b1001_0000 | (i << 5) | parts["psg"]["vol"][i])

    last = parts["psg"]["last"]
    isVolume = last & 0x01
    channel = last >> 1
    src = "vol" if isVolume else "tone"
    lastCmd = 0x80 | (last << 4) | (parts["psg"][src][channel] & 0x0F)
    # print(f"last is {last:02x} command is {lastCmd:02x}")
    psgCmds.append(lastCmd)

    put("psgCmdRegs", psgCmds)

    put("ppiCtrl", [parts["ppi"][0]], 1)
    put("ppiPortC", [parts["ppi"][1]], 1)

    NAMELEN = 0x20-4
    dname = bytearray((" "*NAMELEN).encode("utf-8"))
    for i, c in enumerate(diskname):
        if i < NAMELEN:
            dname[i] = ord(c)
    if len(diskname) > NAMELEN:
        print("WARNING: diskname truncated to", dname)

    put("disk_name", dname)

    srcAddr = le16(FC00_SRC)
    dstAddr = le16(FC00_SRC+1)
    put("patcherCode", srcAddr, 1)
    put("clearSrc", srcAddr, 1)
    put("clearDst", dstAddr, 1)

    if fix_checksum:
        s = sum(ramData[0:0x7FFF]) -\
            sum(ramData[FC00_SRC:FC00_SRC + FC00_SIZE])

        ramData[0x7FFF] = (0x100 - (s & 0xFF)) & 0xFF

    f = scfloppy.Floppy()
    f.verbose = False
    f.format()
    f.addSystem(scfloppy.trackSectorToCluster(0x00, 0), loaderData)
    f.addSystem(scfloppy.trackSectorToCluster(0x01, 0), ramData)
    f.addSystem(scfloppy.trackSectorToCluster(0x15, 0), vramData)

    # plotMap(ramData)
    # plotMap(vramData)

    info = "Tool URL: github.com/fabiodl/floader\r\n"

    names = ["Loader", "RAM   ", "VRAM  "]
    data = [loaderData+patcherData[:patcherCodeSize],
            bytearray(parts["mem"]),
            vramData]
    for n, d in zip(names, data):
        info += f"{n} CRC: {zlib.crc32(d):08X}\r\n"
    info += f"\r\n Type BOOT to launch {diskname}\r\n"
    content = info.encode("UTF-8")
    chunk = bytearray(content) + \
        bytearray([0x1A]+([0x00]*(0x100-len(content)-1)))

    f.addFile(scfloppy.canonicalName("INFO.BAS"),
              open(thisDir()/"info.bas", "rb").read())
    f.addFile(scfloppy.canonicalName("INFO.TXT"), chunk,
              scfloppy.ATTRIBUTE_ASCII)

    f.save(outname)
    if verbose:
        print("Wrote", outname)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert savestates to bootable floppy images')
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("diskname")
    parser.add_argument("--patcher_addr", required=False)
    parser.add_argument(
        '--fix_checksum', action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    patcher_addr = int(args.patcher_addr, 16) if args.patcher_addr else None
    parts = unpackMame.decomposeSavefile(sys.argv[1])
    makeFloppy(str(thisDir()/"loader"), parts, args.output, args.diskname,
               patcher_addr, args.fix_checksum
               )
