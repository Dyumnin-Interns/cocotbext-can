
import logging
from logging import CanFrame
import cocotb
from cocotb.queue import Queue, QueueFull
from cocotb.triggers import RisingEdge, Timer, First, Event
from cocotb.utils import get_sim_time, get_sim_steps
from arbitration import * 
from .version import __version__
from .constant import can_id
from .reset import Reset
from can_frame import CanFrame
from cocotb.binary import BinaryRepresentation, BinaryValue
from cocotb.types import LogicArray


class Cansink(Reset):

    def __init__ ( self, data,can_h  , drive_event , tx_frame , frame=None, reset=None, enable=None, reset_active_level=True, *args, **kwargs): 
        
        self.log = logging.getLogger(f"cocotb.{data._path}")
        self.data = data
        self.can_h = can_h

        self.reset = reset
        #self.enable = enable
        
        self.send_frame=CanFrame(bytearray(), [])
        self.send_frame=frame
        self.log.info("CanSink")
        self.log.info("cocotbext-can version %s", __version__)   
        self.stop_send = Event()
        self.drv = False
        
        self.drive_event = Event()
         
        self.drive_event.add_callback(self.frame_reciecve(drive_event, tx_frame, self.current_frame))
        
        super().__init__(*args, **kwargs)
        
        #self.active = False
        self.active = True
        self.queue = Queue()
        self.active_event = Event()
       

        self.queue_occupancy_bytes = 0
        self.queue_occupancy_frames = 0

        self.width = 8
        self.byte_width = 1
         
        assert len(self.data) == 8
      
        self._run_cr = None
         
        self._init_reset(reset, reset_active_level)
        
    def _recv(self, frame, compact=True):
        if self.queue.empty():
            self.active_event.clear()
        self.queue_occupancy_bytes -= len(frame)
        self.queue_occupancy_frames -= 1
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
    
    
    async def frame_reciecve(self,drive_event, tx_frame):
        drive_event.wait()
        self.send_frame= tx_frame 
            
          
    async def line_error(self , can_l ,can_h):
        line_error=0
        
        while True:
            if(can_h==can_l):
                line_error+=1
                self.line_error_event.set()  
    
    def compare(self, data):
        data.append(0,0)
        if data[-15:-1] == calculate_crc(data[0:-15]):
            return True
        return False
               
         
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
        rtr= False
        ide=False
        ifg = 0 
        
        t=Timer(int(1e9/self.baud),'ns')
         
 
        while True:
            if ~(self.data.value.integer): # waiting for sof  
                rtr= False
                ide=False
                prev_bit=0
                recv = True
                bit_count=0
                end_of_frame= False
                payload= list()
                Total_bits=0
                drve_count= 0
                gap = can_id.GAP_BTN_ID
                
                
            while (recv):
                    await t  
                  #maintian  the recovery from arbitration 
                    if arbitration_event.set():   
                        self.transmit_frame=sender_to_receiver.get()
                        if (bit_count<self.transmit_frame.__len__()): 
                            await t  
                            d = self.data.integer.value
                            if(d_val==prev_bit):
                                drve_count+=1
                            else:
                                drve_count=0
                            if drve_count == 5 :
                                drve_count=0
                            else:          
                                if (d!=self.transmit_frame.data[bit_count]):
                                    if (bit_count<can_id.ID_COUNT):
            
                                       drive_stop_event()  
                                    #  assert lost arbitartion
                                    
                                    elif (bit_count> (can_id.ID_COUNT+gap)) &  (bit_count < can_id.EXT_ID_COUNT):
                                        #assert lost arbitation 
                                        drive_stop_event() 
                                        pass
                                    else:
                                        #asst trsnamission error 
                                        pass
                               
                            bit_count += 1  
                        else:
                            clear_arbitration_event 
                            recv=False 
                            
                    else:   
                           
                        if frame is None:
                                # start of frame
                                frame = CanFrame(LogicArray(), [])
                                frame.sim_time_start = get_sim_time()
                                Receiver_busy()
                            
                        while ( bit_count < Total_bits):                   
                                d_val = self.data.value.integer
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
                                 
                                if (bit_count==can_id.IDE_POSITION):
                                    ide=d_val
                            
                                if (ide):
                                    if (bit_count==can_id.Exten_RTR_POSITION):
                                        rtr= d_val
                                
                                else:
                                    if(bit_count == can_id.RTR_POSITION):
                                        rtr = d_val
                                
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
                            
                    #Acknowledgement
                        
                        if (self.compare(frame.data)):
                            await t 
                            self.data.value.integer  = 0  
                            await t 
                   # for inter frame gap      
                        ifg= can_id.IFG   
                        while (ifg):
                            await t
                            ifg -=1
                            
                        end_of_frame= True       
                        if (end_of_frame):
                                # end of frame                       
                                frame.sim_time_end = get_sim_time()
                                self.log.info("RX frame: %s", frame)
                                if not (self.drv):     
                                    self.queue_occupancy_bytes += len(frame)
                                    self.queue_occupancy_frames += 1
                                    self.queue.put_nowait(frame)
                            #     self.compare_event().set()
                                self.active_event.set()    
                                frame = None
                                payload.clear()
                                bit_count= 0 
                                Receiver_idle()                   
                                end_of_frame= False
                                recv =  False
                 

