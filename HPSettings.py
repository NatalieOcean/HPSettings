# -*- coding: utf-8 -*-
"""
Created on Wed Jul  4 13:32:39 2018

@author: Natalie
"""

import pyzmq
import json
import time
from enum import Enum
from status_reporting import StatusReporting

class Configuration:

    def __init__(self):
        print("Configuration Instantiated")
    
#spectrometer settings    
    scans_to_average = 10
    integration_time_ms = 10
    
    ip_address = "192.168.254.254" # in service it would be localhost
    ip_port = 55557
    
class HPSettings:
    
    def __init__(self, configuration):

        print("Spectrometer Instantiated")
        self.ip_address = configuration.ip_address
        self.ip_port = configuration.ip_port
        self.zmq_context = pyzmq.Context.instance()
        self.zmq_socket = self.zmq_context.socket(pyzmq.DEALER)
        
    def __del__(self):
        self.zmq_context.destroy()

    def get_broker_service_id(self):
        self.zmq_socket.send_multipart([b'BROKER', b'msg&request_services'])  # currently the separator is only &
        reply = self.zmq_socket.recv_multipart(copy=True)
        services = [s for s in reply if (b'rsp&service_info' in s)]
        device_manager_service = [t for t in services if (b'device_manager_service') in t]
        service_id = [s for s in (device_manager_service[0]).decode('UTF-8').split('&') if ('service-id' in s)]
        id = ((service_id[0]).split('=')[1]).encode('UTF-8')
        return  id
    
    def connect(self):
        result = StatusReporting.success
        print("Spectrometer connect")
        if(self.zmq_socket != 0):
            my_ip = 'tcp://' + self.ip_address + ':' + str(self.ip_port)
            self.zmq_socket.connect(my_ip)
            # if there a spectrometer available, don't start the device again. once available it will remain so until
            #  a reboot, even if the zmq socket disconnects
            # For this application, there is only a spectrometer device available. If in the future more devices are
            #  run locally, then the 'first_device' will no longer be valid
            self.zmq_socket.send_multipart([b'BROKER', b'msg&request_devices'])  # currently the separator is only &


            # this could go on one line but it is easier to read using several lines
            device_reply = self.zmq_socket.recv_multipart(copy=True)
            try:
                first_device = str([s for s in device_reply if b'rsp&service_info' in s][0])
                device_characteristics = first_device.split('&')
                self.service_id = (str([s for s in device_characteristics if 'service-id' in s][0]).split('=')[1]).encode('UTF-8')

                #Here for debugging convenience so that the device can be disconnected for the except IndexError to be thrown
                #self.zmq_socket.send_multipart([b'BROKER', b'msg&request_services']) # currently the separator is only &
                #broker_service_id = (str([s for s in str([s for s in self.zmq_socket.recv_multipart(copy=True) if b'rsp&service_info' in s][0]).split('&') if 'service-id' in s][0]).split('=')[1]).encode('UTF-8')
                #self.zmq_socket.send_multipart([broker_service_id, b'msg&disconnect_device&target-id=' + self.service_id])
                #myMessageReceive = self.zmq_socket.recv_multipart(copy=True)

            except IndexError:
                # If no device has been registered, this exception will be thrown.
                # TODO: currently this looks for msg&connect_device. This should be a response rather than a message.
                #  However, the response wrongly sends back msg instead of rsp, so send_receive doesn't work
                # ToDo: given that the spectrometer will always be 127.0.0.1 does a check against a bad ip number need to be made?
                broker_service_id = self.get_broker_service_id()
                self.zmq_socket.send_multipart([broker_service_id, b'msg&connect_device&ip-addr=127.0.0.1'])
                reply = self.zmq_socket.recv_multipart(copy=True)
                self.service_id = (str([s for s in str([s for s in reply if b'msg&connect_device' in s][0]).split('&') if 'service-id' in s][0]).split('=')[1]).encode('UTF-8')
                result = StatusReporting.fail_protocol_no_spectrometer_registered
        return result
    
    def parse_multipart_reply(self, multipart_reply, message, variable_to_get):
        if (multipart_reply[1].decode('UTF-8').split('&')[0].find("err") != -1):
            result = ""
        else:
            command_name = message.split('&')[0]
            response_part = [s for s in multipart_reply if ('rsp&' + command_name).encode('UTF-8') in s]
            result = ([s for s in response_part[0].decode('UTF-8').split('&') if variable_to_get in s][0]).split('=')[1]
        return result

    def send_receive(self, message, variable_to_get):
        self.zmq_socket.send_multipart([self.service_id, ('msg&' + message).encode('UTF-8')])
        reply = self.zmq_socket.recv_multipart(copy=True)
        return self.parse_multipart_reply(reply, message, variable_to_get)

    def send_command(self, message, variables):
        result = StatusReporting.success
        self.zmq_socket.send_multipart([self.service_id, ('msg&' + message + variables).encode('UTF-8')])
        reply = self.zmq_socket.recv_multipart(copy=True)
        if (reply[1].decode('UTF-8').split('&')[0].find("err") != -1):
            result = result = StatusReporting.fail_send_spectrometer_command
        return result
    
    def handle_get_spectrometer_ip(self, ip_addr):
        #return message with spectrometer's ip address
        message = 'msg&get_spectrometer_ip&ip-addr='
        
    def handle_set_spectrometer_ip(self, ip_addr):
        #parse spectrometer's ip address from message and set locally
        
j = json.dumps(['foo', {"bar" : ("baz", 1.0, 2)}])