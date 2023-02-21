.include "memoryMap.i"
.include "ports.i"




.bank BANK_PATCHCODE slot SLOT_PATCHCODE

.define PLACEHOLDER_16 $0000
.define PLACEHOLDER_8 $00


.org 0
patcherCode:
  ld hl,FC00_SRC_ADDR
  ld de,$FC00
  ld bc,FC00_SIZE
  ldir
  xor a
clearSrc:
  ld hl,FC00_SRC_ADDR
clearDst:
  ld de,FC00_SRC_ADDR+1
  ld (hl),a
  ld bc,FC00_SIZE
  ldir
  ld sp,frontRegs
  pop af
  pop bc
  pop de
  pop hl
setSp:
  ld sp,PLACEHOLDER_16
setInterrupt:
  ei
setPc:
  jp PLACEHOLDER_16
frontRegs:
   ;   AF,   BC,   DE,   ; HL,
.dw PLACEHOLDER_16,PLACEHOLDER_16,PLACEHOLDER_16,PLACEHOLDER_16



patcherCodeEnd:


.bank BANK_LOADER slot SLOT_LOADER
.org 0
;    0123456789ABCDEF01  23456789ABCDEF
loaderId:
.db "SYS:"
disk_name:
.db DISK_ID
.repeat $20-4-DISK_ID_LENGTH
.db $00
.endr



;sectors are numbered 1 to 16
;tracks are numbered 0 to 39, but we start placing at 1
;
;  track 01 02 03 04 05 06 07 08 09 0A 0B 0C 0E 0E 0F 10 ;RAM addr 0000 1000 .... F000
;        11 12 13 14 ;VRAM
;
; the IPL uses needs mem from FC00

.define TRACK_VRAM_START $11
.define SECTOR_VRAM_START $01
.define TRACK_VRAM_END $14
.define SECTOR_VRAM_END $10
.define VRAM_BUFFER_ADDR $8000

.define TRACK_RAM_START  $01
.define SECTOR_RAM_START  $01
.define TRACK_RAM_END  $10
.define SECTOR_SAFE_RAM_END  $0C



.org $20
loader:
  call 8      ;track 0
  jp c,0      ;reboot on error
turnOffDisplay:
  ld hl,  ((VDPCMD_REG|$01)<<8)|$80
  ld c,PORT_VDP_CMD
  out (c),l
  out (c),h
copyVram:
  ld de,VRAM_BUFFER_ADDR  ;load start address
  ld bc,(SECTOR_VRAM_START<<8)|TRACK_VRAM_START ;start sector b track c ;sectors start from 1
  ld hl,(SECTOR_VRAM_END<<8)|TRACK_VRAM_END ;end sector b  track c
  call loaderLoop

  xor a
  out (PORT_VDP_CMD),a
  ld a,VDPCMD_VRAM_WR
  out (PORT_VDP_CMD),a

  ld a,0xC0  ; end of vram buffer
  ld hl,VRAM_BUFFER_ADDR
  ld c,PORT_VDP_DATA
  ld b,00
-:otir  ;(C)=(hl)
  cp h
  jp nz,-
copySafeRam:
  ld de,$0000
  ld bc,(SECTOR_RAM_START<<8)|TRACK_RAM_START ;start sector b track c ;sectors start from 1
  ld hl,(SECTOR_SAFE_RAM_END<<8)|TRACK_RAM_END ;end sector b  track c
  call loaderLoop

stopMotor:
  ld a,3 ;motor off
  out ($E7),a
  ld a,$D      ;select
  out ($E7),a  ;0~3FFFF -> ram #1
ppiCtrl:
  ld a,PLACEHOLDER_8
  out (PORT_PPI_CTRL),a
ppiPortC:
  ld a,PLACEHOLDER_8
  out (PORT_PPI_C),a
copyVreg:
  ld c,PORT_VDP_CMD
  ld hl,vdpRegCmds
  ld b,16
  otir
copyProcShadow:
  ld sp,shadowRegs
  pop af
  pop bc
  pop de
  pop hl
  exx
  ex af,af'
  pop ix
  pop iy
copyPsg:
  ld c,PORT_PSG
  ld hl,psgCmdRegs
  ld b,psgCmdRegsEnd-psgCmdRegs
  otir
jumpPatcher:
  jp patcherCode


loaderLoop:
  call $10
  jp c,0
  push hl
  or a
  sbc hl,bc
  pop hl
  ret z
  inc d
  inc b
  ld a,b
  cp $11 ;sector overflow
  jr nz,loaderLoop
  ld b,1
  inc c
  jr loaderLoop




vdpRegCmds:
.db PLACEHOLDER_8,VDPCMD_REG|$00
.db PLACEHOLDER_8,VDPCMD_REG|$01
.db PLACEHOLDER_8,VDPCMD_REG|$02
.db PLACEHOLDER_8,VDPCMD_REG|$03
.db PLACEHOLDER_8,VDPCMD_REG|$04
.db PLACEHOLDER_8,VDPCMD_REG|$05
.db PLACEHOLDER_8,VDPCMD_REG|$06
.db PLACEHOLDER_8,VDPCMD_REG|$07

shadowRegs:
 ;AF2,   BC2,   DE2, HL2,
.dw PLACEHOLDER_16,PLACEHOLDER_16,PLACEHOLDER_16, PLACEHOLDER_16
 ; IX,   IY.
.dw PLACEHOLDER_16,PLACEHOLDER_16


psgCmdRegs:
.db PLACEHOLDER_8,PLACEHOLDER_8        ;tone0
.db PLACEHOLDER_8,PLACEHOLDER_8        ;tone1
.db PLACEHOLDER_8,PLACEHOLDER_8        ;tone2
.db PLACEHOLDER_8                      ;noise
.db PLACEHOLDER_8,PLACEHOLDER_8,PLACEHOLDER_8,PLACEHOLDER_8  ;vol
.db PLACEHOLDER_8                      ;latch
psgCmdRegsEnd:







;mem 64k = 16 tracks
;vram 16k = 4 tracks
;regs= 1 track
