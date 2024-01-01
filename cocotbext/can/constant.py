import enum

# Can_frame
class can_id(enum.IntEnum):
    SOF = 0
    ARBIT = 0x768
    CTRL = 0x44
    
    RB0 = 0
    RB1 = 0
    IDE_POSITION = 13
    RTR_POSITION=14
    
    RTR_bit= 12
    
    GAP_BTN_ID= 3
    ID_COUNT=11
    TOTAL_RTR_BITS= 56
    DLC=4
    
    #FOR EXTENDED 
    EXT_ID_COUNT=29
    Exten_RTR_POSITION = 32
    SRR = 1 
    EXT_DLC=56
    TOTAL_EXT_RTR_BITS= 67
    
    
    
    IFG =8 
