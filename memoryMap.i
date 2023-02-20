.include "diskDefs.i"

.define SLOT_PATCHCODE    0
.define SLOT_LOADER  1

.define PATCHCODE_ADDR $7F1F
.define PATCHCODE_SIZE $E0

.define FC00_SRC_ADDR $C000
.define FC00_SIZE     $0400



                ;0123456789ABCD
.define DISK_ID "SAVESTATE DISK"
.define DISK_ID_LENGTH $0E


.memorymap
defaultslot SLOT_LOADER
slot SLOT_PATCHCODE   PATCHCODE_ADDR PATCHCODE_SIZE
slot SLOT_LOADER LOADER_ADDR FLOPPY_SECTOR_SIZE
.endme


.define BANK_LOADER 0
.define BANK_PATCHCODE 1

.rombankmap
bankstotal 2
banksize FLOPPY_SECTOR_SIZE
banks 1                        ;loader
banksize PATCHCODE_SIZE
banks 1
.endro
