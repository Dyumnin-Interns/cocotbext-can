import logging
from collections import deque
import cocotb
import string 
from cocotb.triggers import RisingEdge , FallingEdge,  Event , Timer 

class Can_Node:

    def __init__(self, canbus , dut=None , baud=9600):
        self.Cannode_sink(self,canbus,dut,baud)
        self.Cannode_source(self,canbus,dut,baud)
        cocotb.start(self.Cannode_sink._recv_active())
        cocotb.start(self.Cannode_sink.error_managaer())
        self.state="Error_Active"
        self.message_id=[]

    #Every node has a list of message if whom they are going to receive  
    #Add and Remove message id     
    def add_message_id(self, message_id):
        self.message_id.append(message_id)
    def rm_message_id(self,message_id):
        self.message_id.remove(message_id)
       
    class Cannode_source:
        def __init__(self, canbus , dut=None , baud=9600):
            if (dut):
                self.dut.can_h=dut.can_h
                self.dut.can_l=dut.can_l
            #self.log=logging.getLogger(f"cocotb.{data.path}")
            self.canbus.can_h=canbus.can_h
            self.canbus.can_l=canbus.can_l
            self.baud= baud
            self._message_queue = deque()
            self.sync =Event()
            self.fork()
                 
            # it will make two process run parrallel 
            # one will check the bittsuffing error 
                      
        async def run(self , frame):
            if (self.dut):
                pass
            else:
                while True:
                    while len(self._message_queue) ==0:
                        self.sync.clear()
                        await self.sync.wait()
                    b= hex((self._message_queue.popleft()).pop())
                    reversed_message = '0x' + format(b, 'x')[::-1]
                    message_bin = bin(int(reversed_message,16))[2:]
                    
                    t=Timer(int(1e9/self.baud),'ns')
                    
                    #start of the frame
                    #it will consist of  
                    self.can_l<=0 
                    self.can_h<=1
                    
                    await t 
                    _stuff_bit_counter=0
                    _prev_bit=0
                    #message frame (arbitration , control , data ,crc )
                    for k in range(frame.length()):
                        bit = message_bin & 1
                        print(f"write bit {k} : {bit}")
                        if(bit==_prev_bit):
                            _stuff_bit_counter+=1
                        if (_stuff_bit_counter==5):
                            self.can_bus.can_h=~(_prev_bit)
                            _stuff_bit_counter=0
                        else:    
                            self.can_l<=bit
                            self.can_h<=~bit
                        _prev_bit=bit
                        message_bin >>=1
                        await t 
                    #end of the frame 
                    self.can_l <= 1 
                    self.can_h <= 0  
                    self.can_l <= 1 
                    self.can_h <= 0 
                    self.can_l <= 1
                    self.can_h <= 0  

            
        async def send(self ,data):
            self.write_nowait(data)
        
        def write_nowait(self, data):
            for b in data:
                self._message_queue.append(b)
            self.sync.set()
            
        #def randomframesend(self,frame_type):
        #    f = can_frame()
        #    self.write_nowait(f)
            
    
    class Cannode_sink:
        
        def __init__(self,canbus, message_id ,  baud=9600):
         #   self.log=logging.getLogger(f"cocotb.{data.path}")
            self.canbus=canbus 
            self.baud= baud
            self.message_id=list(message_id)
            self.queue = deque()
            
            self.sync =Event()
                   
# function will collect the data put it in a queue
        async def collect_data(self):
            #start bit
            _curr_message= "0x" + ""
            t= Timer(int(1e9/self.baud), 'ns')
            await Timer(int(1e9/self.baud/2),'1ns')   
            b=0
            dlc=''
            ide_bit=1
            rtr_bit=0
            count=0
            Total_bits=0
            while(True):
                await t 
                bit = self.can_l.value.integer
                print(f"Read bit {count}: {bit}")
                if (count==13):
                    ide_bit = bit             
                if (ide_bit==0):
                    if(count==14):
                        rtr_bit = bit 
                    if(count>15 and count<20 ):
                        dlc.append(string(bit)) 
                    
                else:
                    if(count==32):
                        rtr_bit = bit

    #check for the number of bytes in the payload  
    # then decide what will be the total number of bits in a single frame 

                if (count>=12 and count<=15):
                    pay_load=pay_load+string(bit)                 
                
                _curr_message.append(bit)
                count+=1

                if(ide_bit==0):
                    if not (rtr_bit):
                        Total_bits = 35+8*int(dlc ,2)
                    else:
                        Total_bits = 30
                else:
                    if not (rtr_bit):
                        Total_bits = 18+35+8*int(dlc,2)
                    else: 
                        Total_bits= 48

                if(count>Total_bits):
                    break
                
            if     
                
                
                
                
          #  await crc_check(self.queue)
       
        async def _recv_active(self):
            consecutive_zeros = 0    
            while True:
                    # Wait for a falling edge to sample the bus
                    yield FallingEdge(self.can_l)
                    # Check the value of the bus signal
                    bus_value = self.canbus.can_l.value.integer
                    while(consecutive_zeros<1):
                    # Check for consecutive '0' bits
                        if bus_value == 0:
                            consecutive_zeros += 1
                        else:
                            consecutive_zeros = 0
                    
                    if consecutive_zeros == 1:
                        # Trigger the coroutine or perform actions when condition is met
                        print("Detected dominant bit!")
                        # coroutine activation 
                        curr_message_id=''
                        _id_bit_count=13
                        t= Timer(int(1e9/self.baud), 'ns')
                        while(_id_bit_count):
                            await t 
                            bit = self.can_l.value.integer
                            if(_id_bit_count==0):
                                if(bit==0):
                                    break
                                else:
                                    _id_bit_count+=18
                            curr_message_id.append(bit)   
                        if curr_message_id in self.message_id:
                            await self.collect_data(self)
                        # Reset the count for next detection
                        consecutive_zeros = 0



       # error handling 
        async def  error_managaer(self):
            pass
            if (self.canbus.can_l ==self.canbus.can_h):
                self._errorcounter+=1
            if (self._errorcounter==127):
                self.state="Error_passive"
                
            if (self._counter>256):
                self.state="Bus_oFf_state"
            
            
            
        async def crc_check(self.queue):
            pass
            
                       
        