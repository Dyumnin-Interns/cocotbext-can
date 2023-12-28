import logging
import struct
import zlib

import cocotb
from cocotb.queue import Queue, QueueFull
from cocotb.triggers import RisingEdge, Timer, First, Event
from cocotb.utils import get_sim_time, get_sim_steps

from .version import __version__
from .constant import can_id, ETH_PREAMBLE
from .reset import Reset


class CanFrame:
    def __init__(self, data=None, error=None, tx_complete=None):
        self.data = bytearray()
        #self.error = None
        self.sim_time_start = None
        self.sim_time_sfd = None
        self.sim_time_end = None
        self.tx_complete = None

        if type(data) is CanFrame:
            self.data = bytearray(data.data)
            #self.error = data.error
            self.sim_time_start = data.sim_time_start
            self.sim_time_sfd = data.sim_time_sfd
            self.sim_time_end = data.sim_time_end
            self.tx_complete = data.tx_complete
        else:
            self.data = bytearray(data)
          #  self.error = error
         
        if tx_complete is not None:
            self.tx_complete = tx_complete

    @classmethod
    def from_payload(cls, payload, min_len=60, tx_complete=None):
        payload = bytearray(payload)
        if len(payload) < min_len:
            payload.extend(bytearray(min_len-len(payload)))
        payload.extend(struct.pack('<L', zlib.crc32(payload)))
        return cls(payload, tx_complete=tx_complete)
    
    @classmethod
    def from_raw_payload(cls,rtr, ide, payload,  tx_complete=None):
        ctrl= bytearray(len(payload))
        ctrl |= RB0 << 5
        if(ide):
              ctrl |= RB1 << 6
              ctrl |= rtr << 7 
        else :
            ctrl |= rtr << 6 
        data = bytearray(can_id.ARBIT)
        data |= sof << 11 
        if(ide):
            extended_arbit=bytearray(extended_arbit)
            extended_arbit |=  ide << 18
            extended_arbit |=  srr << 19
            data.extend(extended_arbit)
        data.extend(ctrl)
        if payload:
          data.extend(payload)    
        return cls.from_payload(data, tx_complete=tx_complete)

   # def get_preamble_len(self):
   #     return self.data.index(EthPre.SFD)+1

   # def get_preamble(self):
   #     return self.data[0:self.get_preamble_len()]

    def get_payload(self, strip_fcs=True):
            if self.data[1]& 1<<3: # check for ide bit 
                if (self.data[4] & 1 ):# check for rtr bit 
                     return 0    
                           
                return self.data[39:-15]
            else:
                if (self.data[1] & 1<< 4):
                    return 0 
                return self.data[18:-15]

    def get_fcs(self):
        return self.data[-4:]

    def check_fcs(self):
        return self.get_fcs() == struct.pack('<L', zlib.crc32(self.get_payload(strip_fcs=True)))

    def normalize(self):
        n = len(self.data)

        if self.error is not None:
            self.error = self.error[:n] + [self.error[-1]]*(n-len(self.error))
        else:
            self.error = [0]*n

   # def compact(self):
   #     if self.error is not None and not any(self.error):
    #        self.error = None

    def handle_tx_complete(self):
        if isinstance(self.tx_complete, Event):
            self.tx_complete.set(self)
        elif callable(self.tx_complete):
            self.tx_complete(self)

    def __eq__(self, other):
        if type(other) is CanFrame:
            return self.data == other.data

    def __repr__(self):
        return (
            f"{type(self).__name__}(data={self.data!r}, "
            f"error={self.error!r}, "
            f"sim_time_start={self.sim_time_start!r}, "
            f"sim_time_sfd={self.sim_time_sfd!r}, "
            f"sim_time_end={self.sim_time_end!r})"
        )

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return self.data.__iter__()

    def __bytes__(self):
        return bytes(self.data)


class Cansource(Reset):

    def __init__(self, data, er, dv, clock, drv_event,tx_frame, reset=None, enable=None,drive_stop =False,  reset_active_level=True, *args, **kwargs):#enable will be used to tell the source when to transfer
        self.log = logging.getLogger(f"cocotb.{data._path}")
        self.data = data
      #  self.er = er
      #  self.dv = dv
        self.clock = clock
        self.reset = reset
        self.enable = enable
        self.drv_event= Event()
        self.drv_event = drv_event()

        self.log.info("Can source")
        self.log.info("cocotbext-can version %s", __version__)
        

        super().__init__(*args, **kwargs)

        self.active = False
        self.queue = Queue()
        self.dequeue_event = Event()
        self.current_frame = None
        self.idle_event = Event()
        self.idle_event.set()
        self.drive_stop= drive_stop
                                    
        self.ifg = 7
       

        self.queue_occupancy_bytes = 0
        self.queue_occupancy_frames = 0

        self.queue_occupancy_limit_bytes = -1
        self.queue_occupancy_limit_frames = -1

        self.width = 8
        self.byte_width = 1

        assert len(self.data) == 8
        self.data.setimmediatevalue(0)
       # if self.er is not None:
        #    assert len(self.er) == 1
         #   self.er.setimmediatevalue(0)
       # assert len(self.dv) == 1
       # self.dv.setimmediatevalue(0)

        self._run_cr = None

        self._init_reset(reset, reset_active_level)

    async def send(self, frame):
        while self.full():
            self.dequeue_event.clear()
            await self.dequeue_event.wait()
        frame = CanFrame(frame)
        await self.queue.put(frame)
        self.idle_event.clear()
        self.active_event.set()
        self.queue_occupancy_bytes += len(frame)
        self.queue_occupancy_frames += 1

    def send_nowait(self, frame):
        if self.full():
            raise QueueFull()
        frame = CanFrame(frame)
        self.queue.put_nowait(frame)
        self.idle_event.clear()
        self.active_event.set()
        self.queue_occupancy_bytes += len(frame)
        self.queue_occupancy_frames += 1

    def count(self):
        return self.queue.qsize()

    def empty(self):
        return self.queue.empty()

    def full(self):
        if self.queue_occupancy_limit_bytes > 0 and self.queue_occupancy_bytes > self.queue_occupancy_limit_bytes:
            return True
        elif self.queue_occupancy_limit_frames > 0 and self.queue_occupancy_frames > self.queue_occupancy_limit_frames:
            return True
        else:
            return False

    def idle(self):
        return self.empty() and not self.active

    def clear(self):
        while not self.queue.empty():
            frame = self.queue.get_nowait()
            frame.sim_time_end = None
            frame.handle_tx_complete()
        self.dequeue_event.set()
        self.idle_event.set()
        self.active_event.clear()
        self.queue_occupancy_bytes = 0
        self.queue_occupancy_frames = 0

    async def wait(self):
        await self.idle_event.wait()

    def _handle_reset(self, state):
        if state:
            self.log.info("Reset asserted")
            if self._run_cr is not None:
                self._run_cr.kill()
                self._run_cr = None

            self.active = False
            self.data.value = 1
          #  if self.er is not None:
          #      self.er.value = 0
          #  self.dv.value = 0

            if self.current_frame:
                self.log.warning("Flushed transmit frame during reset: %s", self.current_frame)
                self.current_frame.handle_tx_complete()
                self.current_frame = None

            if self.queue.empty():
                self.idle_event.set()
                self.active_event.clear()
        else:
            self.log.info("Reset de-asserted")
            if self._run_cr is None:
                self._run_cr = cocotb.start_soon(self._run())

    async def _run(self):
        frame = None
        frame_offset = 0
        frame_data = None
        frame_error = None
        ifg_cnt = 0
        self.active = False

        clock_edge_event = RisingEdge(self.clock)
        
        enable_event = None
        if self.enable is not None:
            enable_event = RisingEdge(self.enable)
        
        while True:
            
            drive= False
            if():
                pass
                byte_value= 0
                byte_index= 0
                drive=True
            
            while(drive):
                if frame is None :
                            frame.sim_time_sfd = get_sim_time()    
                
                await clock_edge_event
                
                if  self.drive_stop :
                # Drive stop event detected
                    if frame is not None:
                        # Put the frame back in the queue
                        self.queue.put_nowait(frame)
                        self.queue_occupancy_bytes += len(frame)
                        self.queue_occupancy_frames += 1
                        frame = None
                        
                        self.current_frame = None
                    
                if not self.drive_stop:
                    if ifg_cnt > 0:
                        # in IFG
                        ifg_cnt -= 1
        
                    elif frame is None and not self.queue.empty():
                        # send frame
                        frame = self.queue.get_nowait()
                        self.dequeue_event.set()
                        self.queue_occupancy_bytes -= len(frame)
                        self.queue_occupancy_frames -= 1
                        self.current_frame = frame
                        frame.sim_time_start = get_sim_time()
                        frame.sim_time_sfd = None
                        frame.sim_time_end = None
                        self.log.info("TX frame: %s", frame)
                        frame.normalize()                        
                        self.active = True
                        frame_offset = 0

                    if frame is not None:
                      #  d = frame_data[frame_offset]
                        
                        if (bit_position==8):
                            byte_index +=1
                         # Iterate through each bit in the byte
                             # Each byte contains 8 bits
                         # Extract the bit using bitwise AND with 1
                        d = (frame.data[byte_index] >> bit_position) & 1  
                                
                        if (prev_bit==d):
                                    tx_count+=1
                        else:
                                    tx_count=0
                        if (tx_count==5):
                                    self.data.value=~prev_bit
                                    tx_count=0
                        else:   
                                    self.data.value = d
                                    prev_bit= d       
                        bit_position +=1

                        if frame_offset >= len(frame_data):
                                    ifg_cnt = max(self.ifg, 1)
                                    frame.sim_time_end = get_sim_time()
                                    frame.handle_tx_complete()
                                    frame = None
                                    bit_position=0
                                    byte_index=0
                                    self.current_frame = None
                    else: 
                        if ifg_cnt == 0 and self.queue.empty():
                            self.idle_event.set()
                            self.active_event.clear()
                            await self.active_event.wait()

                elif self.enable is not None and not self.enable.value:
                    await enable_event


class Cansink(Reset):

    def __init__ ( self, data, er, dv, clock, drv_event,frame_tx , frame=None, reset=None, enable=None, mii_select=None, reset_active_level=True, *args, **kwargs): 
        self.log = logging.getLogger(f"cocotb.{data._path}")
        self.data = data
        self.er = er
        #self.dv = dvvent
        #self.clock = clock
        self.reset = reset
      #  self.enable = enable
        self.drive_stop = Event()
        self.drive_stop = drv_event
        self.send_frame=CanFrame(bytearray(), [])
        self.send_frame=frame
        self.log.info("Can Frame")
        self.log.info("cocotbext-can version %s", __version__)
        if (self.drive_event.set()):
                self.transmit_frame = frame_tx 

        super().__init__(*args, **kwargs)

        #self.active = False
        self.active = True
        self.queue = Queue()
        self.active_event = Event()
        self.stop_send = Event()
        self.drv = False
       
        self.bit_stuff_error = Event()
        self.acknowledge_error = Event()
        
         

        self.queue_occupancy_bytes = 0
        self.queue_occupancy_frames = 0

        self.width = 8
        self.byte_width = 1

        assert len(self.data) == 8
       # if self.er is not None:
     #       assert len(self.er) == 1
      #  if self.dv is not None:
       #     assert len(self.dv) == 1

        self._run_cr = None

        self._init_reset(reset, reset_active_level)

    def _recv(self, frame, compact=True):
        if self.queue.empty():
            self.active_event.clear()
        self.queue_occupancy_bytes -= len(frame)
        self.queue_occupancy_frames -= 1
        if compact:
            frame.compact()
        return frame

    async def recv(self, compact=True):
        frame = await self.queue.get()
        return self._recv(frame, compact)

    def recv_nowait(self, compact=True):
        frame = self.queue.get_nowait()
        return self._recv(frame, compact)

    def count(self):
        return self.queue.qsize()

    def empty(self):
        return self.queue.empty()

    def idle(self):
        return not self.active

    def clear(self):
        while not self.queue.empty():
            self.queue.get_nowait()
        self.active_event.clear()
        self.queue_occupancy_bytes = 0
        self.queue_occupancy_frames = 0
        
    
    def crc15(data):
        """
        Calculates the 15-bit CRC of a byte object and returns it as a byte object.

        Args:
            data: A byte object representing the data to be checksummed.

        Returns:
            A byte object containing the 15-bit CRC value.
        """
        poly = 0x4593  # CRC polynomial for 15-bit CRC
        crc = 0xffff  # Initial CRC value

        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
        crc_bytes = crc.to_bytes(2, byteorder='big')  # Convert CRC to 2-byte byte object
        return crc_bytes[:-1]  # Return only the first 2 bytes (15 bits)
     
    ##    
    async def error_manager(self):
        
       while(True):
            #1.  accknolgement error 
            if (self.acknowledge_error.set()):
                #assert
                pass
            #2.  line error
            my_event = Event("my_event")
            if (my_event): # check whether this event is set or not 
                pass
            #3.  crc error
            if not (self.empty):
                frame= self.queue.get()
                if (frame.data[1]>>4 & 1):
                    if (frame.data[4]>>8 & 1):
                        # calcualte crc
                        pass
                    else:
                        pass 
                else:
                    if (frame.data[1]>>3 & 1 ):
                        pass
                    else:
                        pass   
            #4.  field form bit feild checks
                      
            #5.   bit stuffing
            if (self.bit_stuff_error.set()):
                # assert bit stuffing is encountered 
            
              pass            
             
    async def wait(self, timeout=0, timeout_unit=None):
        if not self.empty():
            return
        if timeout:
            await First(self.active_event.wait(), Timer(timeout, timeout_unit))
        else:
            await self.active_event.wait()
    
    def _handle_reset(self, state):
        if state:
            self.log.info("Reset asserted")
            if self._run_cr is not None:
                self._run_cr.kill()
                self._run_cr = None

            self.active = False
        else:
            self.log.info("Reset de-asserted")
            if self._run_cr is None:
                self._run_cr = cocotb.start_soon(self._run())
            
    async def _run(self):
        frame = None
        self.active = False 
        clock_edge_event = RisingEdge(self.clock) 
        drive_event  = RisingEdge(self.dr) 
       # active_event = RisingEdge(self.dv) 
       # enable_event = None
        prev_bit =  0
        drve_count =  0 
        bit_count=0
       # if self.enable is not None:
        #    enable_event = RisingEdge(self.enable)
        recv = False    
        rtr_or_srr= False
        ide=False
        bit_index = 0
        byte_index = 0
        prev_bit=0
        ifg =0 
        drive_frame = CanFrame(bytearray(), []) 
        while True:
            await clock_edge_event
    
            if (self.data.value.integer): # waiting for sof  
                rtr_or_srr= False
                ide=False
                bit_index = 0
                byte_index = 0
                prev_bit=0
                recv = True
                bit_count=0
                end_of_frame= False
            
           
            while (recv):
                
                #if self.enable is None or self.enable.value:   
                    if self.drive_stop.set():
                        transmit_frame= self.frame_transmit
                    # for Acknolgement      
                    if not (ide):
                            if not (rtr_or_srr): 
                                pass
                                if (bit_count==stand_Ack):
                                    self.data.value.integer = 0          
                            else:
                                if (bit_count==remote_stand_ack):
                                    self.data.value.integer = 0       
                    else:
                        if (bit_count==extended_rtr):
                            if (extended_rtr):
                                if(bit_count==extended_rtr_ack):
                                    self.data.value.integer = 0 
                            else: 
                                if (bit_count == extended_ack):
                                    self.data.value.integer  = 0       
                                      
                    #get the value
                    
                                                             
                    d_val = self.data.value.integer
                # dv_val = self.dv.value.integer
                # er_val = 0 if self.er is None else self.er.value.integer

                  #maintian  the recovery from arbitration 
                    if (self.data.value.integer==1):
                        ide+=1
                    else:
                        idle=0
                    if (idle==7):
                        recv=False
                        self.drive_stop.clear()
                        
                    if drive_event:   
                        if(d_val==prev_bit):
                            drve_count+=1
                        else:
                            drve_count=0
                        if drve_count == 5 :
                            drve_count=0
                        else:      
                            if ( byte_index < len(self.transmit_frame.data)):
                                current_byte = self.transmit_frame.data[byte_index]
                                # Compare each bit in the current byte
                                for bit_shift in range(7, -1, -1):  # Iterate through each bit
                                        received_bit = d_val # d_val
                                        # Extract the bit from the byte_array and compare
                                        drive_frame.data.append(d_val)
                                        mask = 1 << bit_shift
                                        arr_bit = (current_byte & mask) >> bit_shift
                                        if arr_bit != received_bit:
                                            # If any bit doesn't match, return False
                                            self.drive_stop.set()
                                           # frame = CanFrame(bytearray(), [])
                                           # frame.data.extend(drive_frame.data)
                                            drive_frame= None
                                           # raise ValueError("CAN bus is busy - Mismatch detected")  
                                        bit_index += 1
                                byte_index += 1
                            if bit_index == 7:
                                byte_index+=1
                                bit_index =0
                            if byte_index > len(self.transmit_frame.data):
                                byte_index=0
                         
                    else:      
                        if frame is None:
                        # if dv_val:
                                # start of frame
                                frame = CanFrame(bytearray(), [])
                                frame.sim_time_start = get_sim_time()
                                
                        if (end_of_frame):
                        # if not dv_val:
                                #if ():
                                # end of frame                       
                                frame.compact()
                                frame.sim_time_end = get_sim_time()
                                self.log.info("RX frame: %s", frame)
                                
                                if not (self.drv):     
                                    self.queue_occupancy_bytes += len(frame)
                                    self.queue_occupancy_frames += 1
                                    self.queue.put_nowait(frame)
                            #     self.compare_event().set()
                                self.active_event.set()    
                                frame = None
                                end_of_frame= False
                                recv =  False
                                            
                        if frame is not None:
                        #  if frame.sim_time_sfd is None and d_val in (EthPre.SFD, 0xD):
                        #     frame.sim_time_sfd = get_sim_time()
                            #for bit stuffing 
                            if (prev_bit==d_val):
                                count+=1
                            else:
                                count=0
                            if(count==5):
                               count=0
                            if(prev_bit==d_val):
                                self.bit_stuff_error.set()
                        
                            else:
                                frame.data.append(d_val)
                                prev_bit=d_val
                            if (bit_count==13):
                                rtr_or_srr=d_val 
                            if (bit_count==14):
                                ide=d_val
                                
                            bit_count+=1 
                            
                            if (d_val==1):
                                ifg+=1
                            else:
                                ifg=0
                            if (ifg==7): 
                                end_of_frame=True   
                    
                    
                  #  frame.error.append(er_val)

               # if not dv_val:
                #    await active_event

          #  elif self.enable is not None and not self.enable.value:
#                await enable_event


class Canbus:
    def __init__(self, Can_h, Can_l, reset=None, reset_active_level=True, speed=1000e6, *args, **kwargs):
         #canl ,canh,
         
        self.gtx_clk = gtx_clk
        self.can_l = Can_l
        self.can_l = rx_clk
        self.drv_event = Event()
        self.tx_frame= CanFrame(bytearray(), []) 

        super().__init__(*args, **kwargs)
        
        self.tx = Cansink(Can_l , tx_clk,self.drv_event, self.tx_frame, reset, reset_active_level=reset_active_level)
        
        self.rx = Cansource(Can_l, rx_clk,self.drv_event,self.tx_frame, reset_active_level=reset_active_level)
        
        self.rx_clk.setimmediatevalue(0)
        
        self._clock_cr = None
        self.set_speed(speed)
        self.error_count=0
        self.error_=cocotb.start_soon(self.error_manager(Can_l, Can_h ))
        self.can_l = cocotb.start_soon(self.drive_can_h(Can_l, Can_h))
        # phase error self.
    
    async def drive_can_h(self, can_h, can_l):
        pass
        can_h.value.integer = ~ (can_l.value.integer)
    
     
    async def error_manager(self , can_l ,can_h):
        line_error=0
        
        while True:
            if(can_h==can_l):
                line_error+=1
                self.error_event.set()
            
             
    def set_Baud(self, speed):
        if speed in (10e6, 100e6, 1000e6):
            self.speed = speed
        else:
            raise ValueError("Invalid speed selection")

        if self._clock_cr is not None:
            self._clock_cr.kill()
         
        if self.speed == 1000e6:
            self._clock_cr = cocotb.start_soon(self._run_clocks(8*1e9/self.speed))
            self.tx.mii_mode = False
            self.rx.mii_mode = False
            self.tx.clock = self.gtx_clk
        else:
            self._clock_cr = cocotb.start_soon(self._run_clocks(4*1e9/self.speed))
            self.tx.mii_mode = True
            self.rx.mii_mode = True
            self.tx.clock = self.tx_clk
        
        self.tx.assert_reset()
        self.rx.assert_reset()

    async def _run_clocks(self, period):
        half_period = get_sim_steps(period / 2.0, 'ns')
        t = Timer(half_period)
        
        while True:
            await t
            self.rx_clk.value = 1
            self.tx_clk.value = 1
            await t
            self.rx_clk.value = 0
            self.tx_clk.value = 0