import logging
import struct
import zlib

import cocotb
from cocotb.queue import Queue, QueueFull
from cocotb.triggers import RisingEdge, Timer, First, Event
from cocotb.utils import get_sim_time, get_sim_steps

# from .version import __version__
from constant import can_id 
from reset import Reset
from arbitration  import *

from cocotb.binary import BinaryRepresentation, BinaryValue
from cocotb.types import LogicArray


class CanFrame:
    def __init__(self, data=None,tx_complete=None):
        self.data = list()
        self.sim_time_start = None
        self.sim_time_end = None
        self.tx_complete = None

        if type(data) is CanFrame:
            
            self.data= data
            self.sim_time_start = data.sim_time_start
            self.sim_time_sfd = data.sim_time_sfd
            self.sim_time_end = data.sim_time_end
            self.tx_complete = data.tx_complete
        else:
            self.data= data
          
        if tx_complete is not None:
            self.tx_complete = tx_complete

    @classmethod
    def from_payload(cls, payload,  tx_complete=None):
        crc_list= calculate_crc(payload)
        data = payload + crc_list 
        return cls(data, tx_complete=tx_complete)
    
    @classmethod
    def from_raw_payload(cls,rtr, ide, payload, Arbit= None , EXT_id=None  ,tx_complete=None):
        
        pay_load_list = hex_to_binary_list(payload)
        ctrl = ctrl_list(pay_load_list) 
        data=ctrl+pay_load_list
        if ide:
            data.insert(0 , can_id.RB0)
            data.insert(0 , can_id.RB1)
            data.insert(0 , rtr)
            EXT_id_list = hex_to_binary_list(EXT_id)
            data = EXT_id_list + data
            data.insert(0 , ide)
            data.insert(0 , can_id.SRR)
            Arbit = hex_to_binary_list(Arbit)
            data = Arbit + data
        else:
            data.insert(0 , can_id.RB0)
            data.insert(0 , ide)
            data.insert(0 , rtr)
            Arbit = hex_to_binary_list(Arbit)     
            data = Arbit + data
            data.insert(0,0)    
        return cls.from_payload(data, tx_complete=tx_complete)

    
    def get_payload(self):
        payload= self.data[self.message_id_len():can_id.CRC_LENGTH]
        return  payload
           

    def message_id_len(self):
        if (self.data[can_id.IDE_POSITION]):
            return can_id.length_of_ext_message_id
        else:
            return can_id.length_of_std_messgae_id 
        

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
        return bytes(int(len(self.data)/8))
    
    
c1 = CanFrame().from_raw_payload(1, 0, "4599" , Arbit= "4599" ,tx_complete=None)
print(c1.__len__())
