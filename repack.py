import numpy as np
import unpackMame
import sys


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
        if v == 0x00 and addr < 0xFC00:
            return addr
    return 0xC000


def makeFloppy(loadername, parts, outname, diskname="SAVEDATA"):

    with open(loadername+".bin", "rb") as f:
        loaderData = f.read()
    sym = readSymbols(loadername+".sym")

    outData = bytearray([0xFF]*(256*16*40))

    LOADER_START = 0
    LOADER_SIZE = 256
    RAM_START = 256*16*0x01
    RAM_SIZE = 64*1024
    VRAM_START = 256*16*0x11
    VRAM_SIZE = 16*1024

    FC00_SRC = getBigZeroSpace(parts["mem"])
    FC00_SIZE = 0x400

    outData[LOADER_START:LOADER_START+LOADER_SIZE] = loaderData[:LOADER_SIZE]
    outData[RAM_START:RAM_START+RAM_SIZE] = parts["mem"]
    outData[VRAM_START:VRAM_START+VRAM_SIZE] = parts["vram"]

    patcherCodeStart = sym["patcherCode"][1]
    patcherCodeSize = sym["patcherCodeEnd"][1]-patcherCodeStart

    if not isSingleVal(outData[RAM_START + patcherCodeStart:
                               RAM_START + patcherCodeStart+patcherCodeSize], 0xFF):
        print("PATCHER CODE IS OVERWRITING STUFF")

    outData[RAM_START + patcherCodeStart:
            RAM_START + patcherCodeStart+patcherCodeSize] = loaderData[
                0x100:0x100+patcherCodeSize]

    if not isSingleVal(outData[RAM_START+FC00_SRC:RAM_START + FC00_SRC +
                               FC00_SIZE], 0x00):
        print("HIGH RAM IS OVERWRITING STUFF")
        plotMap(parts["mem"])

    outData[RAM_START+FC00_SRC:RAM_START + FC00_SRC +
            FC00_SIZE] = parts["mem"][0xFC00:0xFC00+FC00_SIZE]

    def put(symbol, vals, offset=0):
        sp = sym[symbol]
        if sp[0] == 0:
            start = LOADER_START-0xFF00
        else:
            start = RAM_START
        start += sp[1]+offset
        outData[start:start+len(vals)] = vals
        #print(f"put {hexString(vals)} at {start:04x}")

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

    s = sum(outData[RAM_START:RAM_START+0x7FFF]) -\
        sum(outData[RAM_START+FC00_SRC:RAM_START + FC00_SRC +
                    FC00_SIZE])

    NAMELEN = 0x20-4
    dname = bytearray((" "*NAMELEN).encode("utf-8"))
    for i, c in enumerate(diskname):
        if i < NAMELEN:
            dname[i] = ord(c)

    put("disk_name", dname)

    srcAddr = [FC00_SRC & 0xFF, FC00_SRC >> 8]
    dstAddr = [(FC00_SRC+1) & 0xFF, (FC00_SRC+1) >> 8]
    put("patcherCode", srcAddr, 1)
    put("clearSrc", srcAddr, 1)
    put("clearDst", dstAddr, 1)

    outData[RAM_START+0x7FFF] = 0x100 - (s & 0xFF)

    with open(outname, "wb") as outFile:
        outFile.write(outData)
        print("length ", len(outData))

    print("Wrote", outname)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage "+sys.argv[0]+" inputFile outputFile diskname")
    else:
        parts = unpackMame.decomposeSavefile(sys.argv[1])
        makeFloppy("loader", parts, sys.argv[2], sys.argv[3])
