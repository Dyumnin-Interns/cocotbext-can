
import logging
from logging import CanFrame
from arbitration import  *
import cocotb
from cocotb.queue import Queue, QueueFull
from cocotb.triggers import RisingEdge, Timer, First, Event
from cocotb.utils import get_sim_time, get_sim_steps
from can_frame import CanFrame
from .version import __version__
from .constant import can_id 
from .reset import Reset



class Cansource(Reset):

    def __init__(self,data, can_h, baud_rate , reset=None, reset_active_level=True, *args, **kwargs):#enable will be used to tell the source when to transfer
        # 
        self.log = logging.getLogger(f"cocotb.{data._path}")
        self.data = data
        self.baud = baud_rate
        
        self.log.info("Can source")
        self.log.info("cocotbext-can version %s", __version__)
        
        super().__init__(*args, **kwargs)
        
        self.queue = Queue()
        self.dequeue_event = Event()
        self.current_frame = None
        
        self.idle_event = Event()
        self.idle_event.set()
        #for status of the driver
        self.active_event = Event()
         
        # for arbitration and for idle bus
        self.reset = reset
        #permission 
        
        cocotb.start_soon(self.drive_can_h(data, can_h))
        
        #to transfar data to the reciver
       # self.drive_event = Event()
       # self.drive_event.add_callback(self.send_to_receiver(tx_frame, self.current_frame))
                                    
        self.ifg = 7
              
        self.queue_occupancy_bytes = 0
        self.queue_occupancy_frames = 0

        self.queue_occupancy_limit_bytes = -1
        self.queue_occupancy_limit_frames = -1

        self.width = 8
        self.byte_width = 1
        
        self.data.setimmediatevalue(1)
       

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
        
        
    def send_to_receiver(tx_frame, current_frame):
        tx_frame=current_frame 
          
    async def drive_can_h(data, can_h):
        can_h.value.integer = ~(data.value.integer)
        
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
        ifg_cnt = 0
        self.active = False 
        t=Timer(int(1e9/self.baud),'ns')
            
        while True:
                   
                await t
                if  drive_stop.set():
                # Drive stop event detected
                    if frame is not None:
                        # Put the frame back in the queue
                        self.queue.put_nowait(frame)
                        self.queue_occupancy_bytes += len(frame)
                        self.queue_occupancy_frames += 1
                        frame = None
                        self.current_frame = None
                        
                if Receiver_active.set():
                    
                    if ifg_cnt > 0:
                        # in IFG
                        ifg_cnt -= 1
                    
                    elif frame is None and not self.queue.empty():
                        # send frame
                        frame = self.queue.get_nowait()
                        set_arbitration_event()
                        sender_to_receiver.put(frame)
                        self.dequeue_event.set()
                        self.queue_occupancy_bytes -= len(frame)
                        self.queue_occupancy_frames -= 1
                        self.current_frame = frame
                        bit_position = 0 
                        frame.sim_time_start = get_sim_time()
                        frame.sim_time_sfd = None
                        frame.sim_time_end = None
                        self.log.info("TX frame: %s", frame)
                      #  frame.normalize()                        
                        self.active = True
                        
                    if frame is not None:
    
                         # Iterate through each bit
                        if (bit_position<frame.__len__()):      
                            d = frame.data[bit_position]
                                    
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
                            
                        if  bit_position >= len(frame.__len__()):
                                    ifg_cnt = max(self.ifg, 1)
                                    frame.sim_time_end = get_sim_time()
                                    frame.handle_tx_complete()
                                    frame = None
                                    self.current_frame = None
                    else: 
                        if ifg_cnt == 0 and self.queue.empty():
                            self.idle_event.set()
                            self.active_event.clear()
                            
                    
                    

