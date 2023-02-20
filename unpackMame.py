def decomposeCpu(data):
    regs = ["AF", "BC", "DE", "HL", "IX", "IY",
            "AF2", "BC2", "DE2", "HL2", "SP", "PC", "IFF1", "IFF2"]

    def get(i, r):
        if r in ["IFF1", "IFF2"]:
            return data[i*2]
        else:
            return data[i*2:i*2+2]

    regv = {r: get(i, r) for i, r in enumerate(regs)}
    return regv


def decomposePsg(data):
    tone = []
    vol = []
    for i in range(8):
        v = data[i*2] + (data[i*2+1] << 8)
        if i % 2 == 0:
            tone.append(v)
        else:
            vol.append(v)
    last = data[16]
    return {"tone": tone, "vol": vol, "last": last}


def decomposeSavefile(fname):
    with open(fname, "rb") as f:
        data = f.read()

        RAM_SIZE = 64*1024
        VRAM_SIZE = 16*1024
        VDPREG_SIZE = 8
        PROC_SIZE = 28
        PSG_SIZE = 17
        PPI_SIZE = 2

        start = 0
        mem = data[:RAM_SIZE]
        start += RAM_SIZE
        vram = data[start:start+VRAM_SIZE]
        start += VRAM_SIZE
        vregs = data[start:start+VDPREG_SIZE]
        start += VDPREG_SIZE
        processor = data[start:start+PROC_SIZE]
        start += PROC_SIZE
        psg = data[start:start+PSG_SIZE]
        start += PSG_SIZE
        ppi = data[start:start+PPI_SIZE]
        start += PPI_SIZE

        if start != len(data):
            print("SIZE MISMATCH!!!")

    return {"mem": mem,
            "vram": vram,
            "vregs": vregs,
            "cpu": decomposeCpu(processor),
            "psg": decomposePsg(psg),
            "ppi": ppi
            }
