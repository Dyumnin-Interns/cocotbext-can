
import logging
from logging import CanFrame

import cocotb
from arbitration import *
from cocotb.queue import Queue, QueueFull
from cocotb.triggers import RisingEdge, Timer, First, Event
from cocotb.utils import get_sim_time, get_sim_steps
from can_frame import CanFrame
from .version import __version__
from .constant import can_id
from .reset import Reset


from cocotb.binary import BinaryRepresentation, BinaryValue
from cocotb.types import LogicArray


class CanMonitor(Reset):

    def __init__ ( self, data,can_h , reset=None, enable=None, reset_active_level=True, *args, **kwargs): 
       
        self.log = logging.getLogger(f"cocotb.{data._path}")
        self.data = data
        self.can_h = can_h
        
        self.reset = reset
        
        self.log.info("Can Frame")
        self.log.info("cocotbext-can version %s", __version__)
         
        self.stop_send = Event()
        self.drv = False

        self.drive_event = Event()
          
        super().__init__(*args, **kwargs)
        
        self.active = True
        self.queue = Queue()
        self.active_event = Event()
      
        self.bit_stuff_error = Event()
        self.acknowledge_error = Event()
        self.line_error_event = Event()
        self.field_form_error = Event() 
        cocotb.start_soon(self.error_manager(data, can_h ))
        
        self.queue_occupancy_bytes = 0
        self.queue_occupancy_frames = 0

        self.width = 8
        self.byte_width = 1
         
        assert len(self.data) == 8
      
        self._run_cr = None
         
        self._init_reset(reset, reset_active_level)
        
    def _recv(self, frame):
        if self.queue.empty():
            self.active_event.clear()
        self.queue_occupancy_bytes -= len(frame)
        self.queue_occupancy_frames -= 1
        return frame

    async def recv(self):
        frame = await self.queue.get()
        return self._recv(frame)

    def recv_nowait(self):
        frame = self.queue.get_nowait()
        return self._recv(frame)

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
    
          
    async def line_error(self , can_l ,can_h):
        line_error=0    
        while True:
            if(can_h==can_l):
                line_error+=1
                self.line_error_event.set()  
            
   
    async def error_manager(self):
        
       while(True):
           #1.  accknolgement error 
            if (self.acknowledge_error.set()):
                #assert
                pass
            #2.  line error
            
            if (self.line_error_event.set()): # check whether this event is set or not 
                pass
                #assert

            #3.  crc error
            if not (self.empty):
                frame = self.queue.get().data
                frame.append(0,0)
                if frame[-15:-1] != calculate_crc(frame[0:-15]):
                    #assseter
                    pass
                
            #4.  field form bit feild checks 
            if (self.field_form_error.set()):
                #assert 
                pass        
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
        recv = False    
        rtr_or_srr= False
        ide=False
        t=Timer(int(1e9/self.baud),'ns')
        
        while True:
            
            if ~(self.data.value.integer): # waiting for sof  
                rtr = False
                ide=False
                prev_bit=1
                recv = True
                Total_bits=0
                bit_count=0
                     
            while (recv):
                    await t                  
                    #get the value                         
                    d_val = self.data.value.integer
                                  
                    if frame is None:
                                # start of frame
                                frame = CanFrame(list(), [])
                                frame.sim_time_start = get_sim_time()
                                bit_count = 0 
                                payload=0  
                                                            
                    
                    while (bit_count <= Total_bits):
                            await t 
                            #for bit stuffing 
                            if (prev_bit==d_val):
                                bit_stuff_count+=1
                            else:
                                bit_stuff_count=0
                            if(bit_stuff_count==5):
                                bit_stuff_count=0
                                if(prev_bit==d_val):
                                    self.bit_stuff_error.set()
                            else:
                                frame.data.append(d_val)
                                prev_bit=d_val
                           
                            # for Acknolgement      
                            if not (ide):
                                    if not (rtr_or_srr): 
                                        pass
                                        if (bit_count==can_id.stand_Ack):
                                            if(self.data.value.integer != 0):
                                                self.acknowledge_error.set()                  
                                    else:
                                        if (bit_count==can_id.remote_stand_ack):
                                            if(self.data.value.integer != 0):
                                                self.acknowledge_error.set()   
                            else:
                                if (bit_count==can_id.extended_rtr):
                                    if (can_id.extended_rtr):
                                        if(bit_count==can_id.extended_rtr_ack):
                                            if(self.data.value.integer != 0):
                                                self.acknowledge_error.set()
                                else: 
                                        if (bit_count == can_id.extended_ack):
                                            if(self.data.value.integer != 0):
                                                self.acknowledge_error.set()
                                                                             
                            
        
                            if (bit_count==can_id.ide):
                                ide=d_val
                           
                            if (ide):
                                if (bit_count==can_id.EXT_RTR):
                                    rtr= d_val
                            
                            else:
                                if(bit_count == can_id.RTR):
                                    rtr = d_val
                            
                            #field form error              
                            if (bit_count == can_id.EXT_CRC_DEL): 
                                if (d_val!=1):
                                    self.field_form_error.set() 
                            if (bit_count == can_id.CRC_DEL): 
                                if (d_val!=1):
                                    self.field_form_error.set() 
                            if (bit_count == can_id.EXT_ACK_DEL): 
                                if (d_val!=1):
                                    self.field_form_error.set() 
                            if (bit_count == can_id.ACK_DEL): 
                                if (d_val!=1):
                                    self.field_form_error.set()  
                                    
                                                                                          
                            #to the number of bytes does payload has 
                            if (ide):
                                    if not (rtr):
                                        if (bit_count in can_id.EXT_DLC):
                                            payload.append(d_val)
                                        if payload is not None:
                                            Total_bits = binary_to_decimal(payload)*8 + can_id.TOTAL_EXT_RTR_BITS
                                    else:
                                        
                                        Total_bits = can_id.TOTAL_EXT_RTR_BITS
                                
                            else:
                                    if not (rtr): 
                                        if (bit_count in can_id.DLC):
                                            payload.append(d_val) 
                                        if payload is not None:
                                            Total_bits = binary_to_decimal(payload)*8 + can_id.TOTAL_RTR_BITS
                                    else:
                                        Total_bits = can_id.TOTAL_RTR_BITS
                            
                            bit_count+=1 
                         
                    # end of frame 
                    EOF = can_id.EOF  
                    while(EOF):
                        await t 
                        if (self.data.integer.value==0):
                            self.field_form_error.set() 
                        EOF-=1
                                                                 
                    frame.sim_time_end = get_sim_time()
                    self.log.info("RX frame: %s", frame)             
                    self.active_event.set()    
                    frame = None
                    recv= False
                                                                      
            
                    
                               
                 

