from can_driver import Cansource
from can_receiver import Cansink
from can_monitor import CanMonitor
from .version import __version__

from .reset import Reset

class Canbus(Reset):
    
    def __init__(self, Can_h, Can_l, baud_rate,reset=None, reset_active_level=True , *args, **kwargs):
        #canl ,canh,
         
        super().__init__(*args, **kwargs)
                 
        self.tx = Cansink(Can_l,Can_h,baud_rate,reset=None, reset_active_level=reset_active_level)
               
        self.rx = Cansource(Can_l,Can_h,baud_rate, reset_active_level=reset_active_level)
        
        self.monitor = CanMonitor(Can_l,Can_h, reset=None, reset_active_level=True, *args, **kwargs)
          

