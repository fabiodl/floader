# floader
Convert SC3000 savestates to SF7000 floppies


Usage 
run mame with the console active
mame -window -plugin console sc3000  -cart Basic.sc  -cass mytape.wav

in MAME console, load the save script by
dofile("save.lua")

in MAME console when desired, save the state by
save("mystate.bin")

convert the save state to floppy by
python3 repack.py mystate.bin mystate.sf7 "MY TAPE"






