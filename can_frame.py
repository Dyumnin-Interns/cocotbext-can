import binascii
import string 
from collections import queue 


class Can_frame:
    arbit : string 
    ctrl  : string
    data  : string
    crc   : string
    length: int  
    


    
    def __init__(self, arbit , ctrl , data):
        #self.arbit = arbit
        #self.ctrl  = ctrl 
        #self.data = data
        self.crc = self.make_crc(arbit,ctrl ,data)
        self.message = self.make_message()
        #self.message = self.arbit+self.ctrl+self.data+self.crc
        
        
    def make_crc(self ,arbit , ctrl ,data):
        message_id_with_data= arbit+ ctrl+ data
        #polynomial for 15 bit crc field
        poly = int("C599", 16)
        data_bytes = bytes.fromhex(message_id_with_data)
        # Calculate CRC
        crc = binascii.crc_hqx(data_bytes, poly)
        return crc 
    
    def length(self):
        return len(self.arbit+self.ctrl+self.data+self.crc)
    
    def make_message(self , arbit , ctrl ,data , crc ):
        totoal_message = arbit+ctrl +data+ string(crc)
        for k in totoal_message:
            self.queue().append(int(k))