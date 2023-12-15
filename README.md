# cocotbext-can

##introduction 
The CAN (Controller Area Network) protocol facilitates vehicle multi-node communication through dual-wire signaling (CANH, CANL). Messages with unique identifiers are broadcasted on the bus, allowing nodes to interpret and act upon relevant data. This message-based system enables efficient, real-time data exchange crucial for automotive functionalities and control. This document supports can 2.0b.
For the simulation of a can protocol 


##Installation

Installation from pip (release version, stable):
```
$ pip install cocotbext-can
```
Installation from git (latest development version, potentially unstable):
```
$ pip install https://github.com/Dyumnin-Interns/cocotbext-can/archive/master.zip
```
Installation for active development:
```
$ git clone https://github.com/Dyumnin-Interns/cocotbext-can
$ pip install -e cocotbext-can
```


##Documentation and usage examples

There are 3 classes present  
Cannode
Canframe
Canbus 

##Cannode 
This class implements a node that can send and receive message frames (data frame and remote frame). Multiple cannode can be instantiated to increase the traffic on the bus. Each cannode can drive and receive a message frame from the bus. The cannode class is a wrapper around cannodeSource and cannodeSink that also provides a baud rate for the transmission. The cannodeSource drives canframe into a design. The cannodeSink receives canframe, including monitoring internal interfaces. When a dominant bit(0) appears on the bus,  the nodes will compare the message ID and receive the frame from the bus. Otherwise, the bus will be in a recessive state (1).
There is a method check() which can be used for checking errors in a frame if the error is found it will change the error counter value accordingly. It is based on the CRC field which is a part of the frame. The Typeof_frame method is there to modify the frame the type of frame (remote or data ).
For the arbitration cannode will check the bus also if another node has put a dominant bit, then it will stop the transfer.   
To use this class 
from cocotext.can import CanBus, CanNode
```
node = Cannode(CanBus, messge_id , dut.rst)
```
for a frame, we must provide a message field, control field, and the data field. If the data field is not provided then it automatically makes it a remote frame. The CRC field will be generated based on the other field provided. 
await node.cannodesource.send(frame)

there is no method for receiving the message. If a node finds a message-id relevant then it automatically captures that frame. And put it in a received fifo.  
Then to access the queue.
``` 
Data = Node.cannodesink.Read()
Data = node.cannodesink.top()
```
To check the the frame error through CRC a method is provided which will require a message and give Boolean output. 
```
Node.check(data)
```
For further addition of the message-id here a method is provided append().
Constructor parameter
Message-id: message-id relevant for a node for the receiving.
Bus: canbus object containing interface signals 
reset: reset signal (optional)  
Methods 
Wait_send(): wait for the bus to idle and then transfer 
Send(frame): send the message frame 
Read(): to get the first data present on the node
Top(): get the first data present on the node (it doesn’t remove it)
Rxercount(): return the number of error counts for receiving 
Set_baud(): set the baud rate for the transmission  
Idle(): return true if no transfer is pending 
Check(): it will check the frame for the error 
Append(): to add the message id to a node
Attribute
Data: access the data field from a frame 
nodeerror: number of errors encountered 

##Canframe 
It implements the frame to be transferred from one node to another node 
The canFrame object is a container for a frame to be transferred via canbus. Here frame can be two types remote and data frame but default frame would be a data frame but the type can be changed by the sending node. 
Each message frame contains 
SOF (Start of Frame) - Marks the beginning of data and remote Frames
Arbitration Field – Includes the message ID and RTR (Remote Transmission Request) bit, which distinguishes data and remote frames
Control Field – Used to determine data size and message ID length
Data Field – The actual data (Applies only to a data frame, not a remote frame)
CRC Field - Checksum
ACK Field – Acknowledgement of checksum check
EOF (End of Frame) – Marks the end of data and remote frames
Constructor parameter
size_of_frame: standard(0) or extended(1)   
Arbitration_field: contains the message-id  
Control_field: information about the data 
Data_field: contain the data(optional) 
Attribute 
CRC_Field: Checksum for the frame 
Method 
Type_of_frame(): returns the type of frame remote or data. 

Canbus is an extended class from cocotb.bus. here canbus is implemented as a double-ended signal. canbus object that contains data signal. The bus will also monitor the error occurring on the bus with the help of an error counter it will monitor two types of error transmission bit error (canh and canl are out of phase) and bit flip error(CRC) and give the number of error occurred.
Signals 
CanH: it contains the signals for the transmission 
CanL: It is an inversion of the canH signal 
Method :
errorcount():will return the number of errors detected on the bus 


example   
```    
from cocotbext.can import CanBus, CanNode, CanFrame

##node is instantiated message-id is provided for the receiving message  
node1 = CanNode(CanBus, 0X019 , dut.rst) 
await node1.append(0X004)
frame1 = CanFrame(0 , 0X007, 0x03, 0x0130)
await node.cannodesource.send(frame1)

#to get the data from the queue 
Data0 = Node1.cannodesink.Read()
Data1 = node1.cannodesink.top()
#to check the error on the bus 
await Canbus.error()
```
