from cocotb.triggers import Event
from cocotb.queue import Queue, QueueFull
# Create a global event object using cocotb

arbitration_event = Event()
drive_stop = Event()
Receiver_active = Event()

sender_to_receiver=Queue(1)
# Function to set the global event
def set_arbitration_event():
    arbitration_event.set()

# Function to clear the global event
def clear_arbitration_event():
    arbitration_event.clear()
    
# Function to set the global event
def drive_stop_event():
    drive_stop.set()

# Function to clear the global event
def drive__event():
    drive_stop.clear()

def  Receiver_busy():
    arbitration_event.set()

# Function to clear the global event
def Receiver_idle():
    arbitration_event.clear()
    
        
def hex_to_binary_list(hex_number):
    # Convert hex to binary string and remove the '0b' prefix
    binary_string = bin(int(hex_number, 16))[2:]
    
    # Pad the binary string to ensure its length is a multiple of 8
    padding_length = (8 - (len(binary_string) % 8)) % 8
    binary_string = '0' * padding_length + binary_string
    binary_list=[]
    # Split the binary string into chunks of 8 bits (1 byte) and convert to integers
    for i in binary_string: 
        binary_list.append(int(i))     
    return binary_list
# Example usage


def ctrl_list(input_list):
    # Get the length of the input list and convert it to binary with a maximum of 4 bits
    binary_length = bin(len(input_list))[2:]
    
    # Ensure the binary length is no more than 4 bits by truncating or padding
   
    binary_length = '0' * (4 - len(binary_length)) + binary_length
    
    # Convert the 4-bit binary representation to integers
    binary_list=[]
    # Split the binary string into chunks of 8 bits (1 byte) and convert to integers
    for i in binary_length: 
        binary_list.append(int(i))     
    return binary_list


def calculate_crc(input_data):
    crc = 0
    polynomial = 0x4599  # CRC polynomial

    for bit in input_data:
        crc ^= bit << 14  # XOR the most significant bit of CRC with the current data bit
        if crc & (1 << 14):  # Check if the most significant bit of CRC is 1
            crc = (crc << 1) ^ polynomial  # Perform polynomial division if necessary
        else:
            crc <<= 1  # Shift the CRC to the left

        crc &= 0x7FFF  # Keep the CRC within 15 bits
        
    
    
    crc_list= []
    crc_bin= bin(crc)[2:]
    for i in crc_bin:
        crc_list.append(int(i))
    return crc_list


def binary_to_decimal(binary_list):
    decimal = 0
    power = len(binary_list) - 1

    for bit in binary_list:
        decimal += bit * (2 ** power)
        power -= 1

    return decimal
