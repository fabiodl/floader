


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



function waitGood(limit)
   local cpu=manager.machine.devices[":z80"]
   local psg = manager.machine.devices[":sn76489an"]
   local psgreg = emu.item(psg.items["0/m_register"])
   clocks=0
      
   for clocks=0,limit do
      emu.step()
      local sound=false
      local intr=cpu.state["IFF1"].value~=cpu.state["IFF2"].value
      for i=1,7,2 do
         if psgreg:read(i)~=0xF then
            sound=true
            break
         end
      end      
      if  not intr and not sound then
         break
      end
   end
   return intr,sound 
end


function save(filename)
   emu.pause()
   filename = filename or "out.bin"
   intr,sound=waitGood(20000000)
   if intr then
      print("warning, inside interrupt")
   end
   if sound then
      print("warning, sound active")
   end
   dump(filename)
   print("Save of "..filename.." complete")
   emu.unpause()
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