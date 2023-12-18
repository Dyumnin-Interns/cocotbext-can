
import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer , Event
from cocotb_bus import drivers ,monitors ,scoreboard 
from cocotb.queue import Queue
import string

class can_bus(monitors):

    global ide_bit , dlc , rtr_bit , payload 

    def __init__(self):
        self.can_h
        self.can_l
        self.queue  = Queue()
        self.bit_flip_error_count=0
        
# function will collect the data put it in a queue
    async def collect_data(self):
        #start bit
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
            b != bit<<count
            self.queue.append(b)
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
       
    async def activate_on_condition(self):
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
                        await self.collect_data(self)
                        # Reset the count for next detection
                        consecutive_zeros = 0

    async def check(self):
         if (self.can_h ==self.can_l):
              bit_flip_error_count+=1
    
    async def crc_error_check():
         if(ide_bit==0):
            pass    
              



