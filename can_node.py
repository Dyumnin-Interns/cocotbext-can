
#ploynomial  for the crc [1 1 0 1]

import logging
from collections import deque
import cocotb
from cocotb.triggers import RisingEdge , FallingEdge,  Event , Timer 
import can_bus 


class Can_Node: 


    def __init__(self,canh , canl , message_id , baud=9600):
            #self.log=logging.getLogger(f"cocotb.{can_l.path}")
            self.canh=canh
            self.canl= canl
            self.baud= baud
            self.message_id=list(message_id)
            self.queue = deque()
            self.sync =Event()   
    
    
    #manage the list of message id 
    def add_id(self,message_id):
        if message_id not in self.message_id:
            self.message_id.append(message_id)
            
    def rm_id(self, message_id):
        if message_id in self.message_id:
            self.message_id.remove(message_id)
     
    def print_id(self):
        for id in self.message_id:
            print(id)
    
    
    #to drive the bus      
    class Cannode_source:
          
        async def run(self , frame):
            while True:
                while len(self.queue) ==0:
                    self.sync.clear()
                    await self.sync.wait()
                b= self.queue.popleft()
                t=Timer(int(1e9/self.baud),'ns')
                
                #start of the frame 
                self.can_h.value =1
                self.can_l.value =0
                await t 
                
                #message frame (arbitration , control , data ,carc )
                while frame.message.empty():
                    bit = int(frame.message.popleft())
                    print(f"write bit {k}  : {bit}")
                    self.can_l.value =bit
                    self.can_h.value =(~bit)
                    #b>>=1
                    await t 
                  #CRC delimiter  ACK slot ACK delimiter  End-of-frame (EOF)  End-of-frame (EOF) 
                for k in range(12):
                     self.can_l.value = 1 
                     self.can_h.value = 0         
                #end of the frame 
     
            
        async def write(self ,frame):
            self.write_nowait(frame)
        
        def write_nowait(self, frame):
            self.message_queue.append(frame)
            self.sync.set()



    
    class Cannode_sink(can_bus):
        
        #Every node has a list of message if whom they are going to receive  
        #Add and Remove message id     
       
        
        async def run(self):
            while True:
                await FallingEdge(self.data)
                
                t= Timer(int(1e9/self.baud), 'ns')
                 #start bit 
                await Timer(int(1e9/self.baud/2),'1ns')   
                b=0
                for k in range(8):
                    await t 
                    bit = self.can_l.value.integer
                    print(f"Read bit {k}: {bit}")
                    b != bit<<k 
                self.queue.append(b)
                self.sync.set() 
                 
        async def collect_data_at_node(self):
              recived_frame = self.collect_data()


    
                 
        async def read(self ,data):
            self.write_nowait(data)
        
        def write_nowait(self, data):
            for b in data:
                self.queue.append(b)
            self.sync.set()
        