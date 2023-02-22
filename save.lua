


function dumpPsg(f)
   local psg = manager.machine.devices[":sn76489an"]
   local psgreg = emu.item(psg.items["0/m_register"])
   local last=emu.item(psg.items["0/m_last_register"])
   --tone 0
   --vol 0
   --tone 1
   --vol 1
   for i=0,7 do
      local v=psgreg:read(i)
      -- print(v)
      f:write(string.pack("I2<",(v)))
   end
   local v=last:read(0)
   f:write(string.char(v))

end


function dumpRam(f)
   local cpu=manager.machine.devices[":z80"]
   local mem=cpu.spaces["program"]
   for addr = 0, 0xFFFF do
      local v=mem:read_u8(addr)
      f:write(string.char(v))
   end
end


function dumpCpu(f)

   local cpu=manager.machine.devices[":z80"]

   local regs={"AF","BC","DE","HL","IX","IY",
      "AF2","BC2","DE2","HL2","SP","PC","IFF1","IFF2"
   }

   for _,reg in pairs(regs) do
      local val=tonumber(tostring(cpu.state[reg]),16)
      -- print(reg,cpu.state[reg])
      f:write(string.pack("I2<",val))
   end


end



function dumpVdp(f)
   local vdp=manager.machine.devices["tms9918a"]
   local vram=emu.item(vdp.items["1/0-3fff"])
   for addr=0,0x3FFF do
      local v=vram:read(addr)
      f:write(string.char(v))
   end

   for i=0,7 do
      local v=emu.item(vdp.items["0/m_Regs["..i.."]"]):read(0)
      -- print(string.format("%02x",v))
      f:write(string.char(v))
   end

end

function dumpPPI(f)
   -- A input
   -- B input
   -- C output
   local ppi = manager.machine.devices[":sgexp:sk1100:upd9255_0"]
   -- printAll(ppi.items)
   local ppiControl = emu.item(ppi.items["0/m_control"]):read(0)
   local ppiC = emu.item(ppi.items["0/m_output"]):read(2)
   f:write(string.char(ppiControl))
   f:write(string.char(ppiC))
end



function dump(filename)
   local f=assert(io.open(filename,"wb"))
   dumpRam(f)
   dumpVdp(f)
   dumpCpu(f)
   dumpPsg(f)
   dumpPPI(f)
   f:close()
end



function isGood()
   local cpu=manager.machine.devices[":z80"]
   local psg = manager.machine.devices[":sn76489an"]
   local psgreg = emu.item(psg.items["0/m_register"])

   local intr=cpu.state["IFF1"].value~=cpu.state["IFF2"].value
   local sound=false

   for i=1,7,2 do
      if psgreg:read(i)~=0xF then
         sound=true
         break
      end
   end

   return intr,sound
end



function save_callback()
   if outFilename~=nil then
      if manager.machine.paused then
         local intr,sound=isGood()
         local saveReady= (not intr and not sound) or manager.machine.time.seconds>timeLimit
         if saveReady then
            if intr then
               print("warning, inside interrupt")
            end
            if sound then
               print("warning, sound active")
            end
            dump(outFilename)
            print("Save of "..outFilename.." complete")
            outFilename=nil
            emu.unpause()
         else
            emu.step()
         end
      end
   end
end



function save(filename)
   if not callbackRegistered then
      emu.register_frame_done(save_callback)
      callbackRegistered=true
   end
   timeLimit=manager.machine.time.seconds+5
   outFilename = filename or "out.bin"
   emu.pause()
end



function printAll(x)
   for k,v in pairs(x) do
      print(k,v)
   end

end

function printShape(x)
      print(x.size,x.count)
end

function deb()
   printAll(manager.machine.devices)
   local ppi = manager.machine.devices[":sgexp:sk1100:upd9255_0"]
   printAll(ppi.items)
   local ppiControl = emu.item(ppi.items["0/m_control"])
   local ppiOutput = emu.item(ppi.items["0/m_output"])
   printShape(ppiControl)
   printShape(ppiOutput)
end
