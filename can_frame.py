import binascii
import string
import logging
import cocotb.queue

class Can_frame:
    def __init__(self,arbit, ctrl, data=None,Error_frame=False,type_error=0):
        if Error_frame:
            #for error frame 
            self.error_frame(self,type_error)
        else:
            self.arbit = arbit
            self.ctrl = ctrl[2:]
            self.data = data[2:]
            self.crc = self.make_crc()[2:]
            self.message = self.make_message()
            
    def make_crc(self):
        message_id_with_data = self.arbit + self.ctrl + self.data
        poly = 0xC599
        data= int(message_id_with_data,16)
       #data_bytes = bytes.fromhex(message_id_with_data)
        crc = hex(data%poly) 
        #crc = binascii.crc_hqx(data.to_bytes(2,'big'), poly.to_bytes(2,'big'))
        return crc

    def length(self):
        return len(self.message)*4

    def make_message(self):
        total_message = self.arbit + self.ctrl + self.data + str(self.crc)
        # Processing the message into a format (here, appending each character's integer value)
        message = []
        for char in total_message:
            message.append(char)
        return message
    
    
    def frame_feature(self):
        self.log = logging.getLogger("Frame chracterstics")
        if(self.length()>136):
            self.log.info("Extended 2.0b FRAME")
        else:
            self.log.info("Standard 2.0b FRAME")
            
        if (self.ctrl[0]=='1'):
            self.log.info("REMOTE FRAME ")
        else:
            self.log.info("DATA FRAME")
                
       # if(self.Error_frame):
       #     self.log.info("ERROR FRAME")    
            
         #   error frame  
    def error_frame(self, type=0):
        if(type==0):
            pass
        else:    
            self.error()
            
    #error frame  
    def error_frame(self, type=0):
        if(type==0):
            pass
        elif(type==1):    
            self.error()
        else:
            pass



frame1 = Can_frame("0x997","0x90a" , "0x098ad")
frame1.frame_feature()
