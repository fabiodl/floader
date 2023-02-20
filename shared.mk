SELF_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
WLA_DIR=$(HOME)/git/wla-dx/binaries/
ASM=$(WLA_DIR)wla-z80
LINKER=$(WLA_DIR)wlalink

ifndef SRC
SRC=$(wildcard *.asm)
endif

OBJ = $(patsubst %.asm, build/%.o, $(SRC))



all: $(PROGNAME).$(EXT)

$(PROGNAME).$(EXT): $(OBJ) $(PROGNAME).lkr
	$(LINKER) -d -r -v -s $(PROGNAME).lkr $(PROGNAME).$(EXT)

$(PROGNAME).lkr: $(OBJ)
	echo [objects]> $(PROGNAME).lkr
	echo $(OBJ) | sed -e 's/ /\n/g' >> $(PROGNAME).lkr

build/%.o: %.asm build
	$(ASM) $(ASMFLAGS) -o $@ $<

build:
	mkdir -p build

clean:
	rm -r build $(PROGNAME).sym $(PROGNAME).lkr $(PROGNAME).$(EXT)
