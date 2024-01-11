import asyncio
import logging
import math
import queue
import random
import time
from typing import Any, Dict, List, Set
from datetime import datetime, timedelta, timezone

from matter_testing_support import MatterBaseTest, default_matter_test_main, async_test_body
from chip.interaction_model import Status as StatusEnum
from chip.utils import CommissioningBuildingBlocks
import chip.clusters as Clusters
from mobly import asserts

class improved_large_network(MatterBaseTest):
    
    def logging_object_attributes(self, dev_ctrl):
        logging.info(f"Attributes of Clusters: {dir(Clusters)}")
        logging.info(f"Attributes of door lock: {dir(Clusters.DoorLock)}")
        logging.info(f"Attributes of door lock attributes: {dir(Clusters.DoorLock.Attributes)}")
        logging.info(f"Attributes of door lock commands: {dir(Clusters.DoorLock.Commands)}")
        logging.info(f"dev_ctrl: {dir(dev_ctrl)}")

    def logging_statistics(self, time_elapsed, num_messages, num_errors, node_id_errors, node_error_rate, error_timestamps, final_node_error_max_time, node_latency, periodic_check_node_error_rate, periodic_node_latency, periodic_check):
        logging.info("Network Test Statistics")
        logging.info("***************************************************************")
        logging.info(f"Time Elapsed: {time_elapsed}")
        logging.info(f"Total number of messages sent in network: {num_messages}")
        logging.info(f"Total number of error messages in network: {num_errors}")
        logging.info(f"Periodic Check Value: {periodic_check}")
        for key, value in node_id_errors.items():
            logging.info(f"Node {key} errors: {value}")
        logging.info("")
        
        if periodic_check == True:
            for key, value in periodic_check_node_error_rate.items():
                logging.info(f"Node {key} Error Rate: {value}")
            logging.info("")
        
        for key, value in error_timestamps.items():
            logging.info(f"Error {key} Timestamps: {value}")
        logging.info("")
        
        for key, value in final_node_error_max_time.items():
            logging.info(f"Node {key} max synchronization loss duration: {value}")
        logging.info("")
        
        #Depending on if we are doing a periodic check or not, the value of node latency will differ on being the total latency (True) or the average latency (False)
        if periodic_check == True:
            for key, value in node_latency.items():
                logging.info(f"Node {key} total latency: {value}")
            for key, value in periodic_node_latency.items():
                logging.info(f"Node {key} average latency: {value}")
            logging.info("")

        else:
            for key, value in node_latency.items():
                logging.info(f"Node {key} average latency: {value}")
            logging.info("")
        logging.info("***************************************************************")


    def file_output(self, time_elapsed, num_messages, num_errors, node_id_errors, node_error_rate, error_timestamps, final_node_error_max_time, node_latency):
        file = open("error_statistics.txt", "w")
        file.write("Network Test Statistics \n")
        file.write("******************************************************************** \n")
        file.write("Time Elapsed: {0}\n".format(str(time_elapsed)))
        file.write("Total number of messages sent in network: {0}\n".format(str(num_messages)))
        file.write("Total number of error messages in network {0}\n".format(str(num_errors)))
        for key, value in node_id_errors.items():
            file.write("Node {0} errors: {1} \n".format(key, value))
        file.write("\n")
        for key, value in node_error_rate.items():
            file.write("Node {0} error rate: {1} \n".format(key, value))
        file.write("\n")
        for key, value in error_timestamps.items():
            file.write("Error {0} timestamps: {1}\n".format(key, value))
        for key, value in final_node_error_max_time.items():
            file.write("Node {0} max synchronization loss duration: {1}\n".format(key,value))
        for key, value in node_latency.items():
            file.write("Node {0} average latency: {1}\n".format(key,value))

    @async_test_body
    async def test_improved_large_network(self):
        dev_ctrl = self.default_controller
        logging.info("Commissioning is complete")
        #logging.info("60 second delay to give FTD time to setup")
        #time.sleep(50)
        #logging.info("10 seconds remaining")
        #time.sleep(10)
        self.logging_object_attributes(dev_ctrl)
        logging.info("Attempting to read attributes")
        logging.info(f"All node ids: {self.all_dut_node_ids}")
        logging.info("-------------------------------------------------------------------------")
        
        #Contains the messageID of the errors for each node 
        node_id_errors = {key: [] for key in self.all_dut_node_ids}
        #Error rate for each node
        node_error_rate = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        #For the periodic logging, find the error rate for each node without messing with the actual error rate
        periodic_check_node_error_rate = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        #The current sequence of errors synchronization loss for a node
        node_error_max_time = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        #The maximum error synchronization loss for all nodes
        final_node_error_max_time = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        #Message latency for all nodes
        node_latency = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        #For the periodic logging, find the node latency for each node without messing with the actual total latency
        periodic_node_latency = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        #Boolean dictionary for if we have back to back errors for that node, used to determine if we should start calcuating the error synchronization loss for the current node
        consecutive_errors = dict(zip(self.all_dut_node_ids, [False]*len(self.all_dut_node_ids)))
        #Contains the previous failed message timestamp (taken from after we know it has failed)
        node_failed_message_timestamp = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))

        error_timestamps = {}
        num_messages = 0
        num_errors = 0
        loop_boolean = True
        start_time = time.time()

        try:
            while loop_boolean == True:
                for i in self.all_dut_node_ids:
                    time_elapsed = time.time() - start_time
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-5]
                    logging.info(f"MessageID: {num_messages}")
                    logging.info(f"Time Elapsed: {time_elapsed}")
                    logging.info(f"Reading attribute for node {i}:")
                    message_start_timestamp = time.time()

                    try:
                        attribute_state = await dev_ctrl.ReadAttribute(i, [Clusters.OnOff])
                        message_end_timestamp = time.time()
                        logging.info(f"Latency to be added: {message_end_timestamp - message_start_timestamp}")
                        current_error_time = (message_end_timestamp - message_start_timestamp)
                        node_latency[i] += current_error_time
                        
                        if consecutive_errors[i] == True:
                            logging.info(f"Prior to this messsage, there has been at least one error at node {i}")
                            node_error_max_time[i] = message_end_timestamp - node_error_max_time[i]
                            consecutive_errors[i] = False

                            logging.info(f"Current set of errors synchronization loss time: {node_error_max_time[i]}")
                            logging.info(f"Max synchronization loss time: {final_node_error_max_time[i]}")
                        if final_node_error_max_time[i] < node_error_max_time[i]:
                            logging.info("Current set of errors has a larger synchronization loss time; updating max synchronization loss time")
                            final_node_error_max_time[i] = node_error_max_time[i]
                        node_error_max_time[i] = 0

                    #When we force stop the test during the looping of reading from all devices
                    except KeyboardInterrupt:
                        messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
                        #Set Error Rate
                        logging.info(f"Messages sent per device: {messages_sent_per_device}")
                        for node_id in self.all_dut_node_ids:
                            node_error_rate[node_id] = (node_error_rate.get(node_id) / messages_sent_per_device)
                            logging.info(f"Node {node_id} total latency {node_latency[node_id]}")
                            node_latency[node_id] = (node_latency[node_id] / messages_sent_per_device)

                        self.logging_statistics(time_elapsed, num_messages, num_errors, node_id_errors, node_error_rate, error_timestamps, final_node_error_max_time, node_latency, periodic_check_node_error_rate, periodic_node_latency, False)

                        self.file_output(time_elapsed, num_messages, num_errors, node_id_errors, node_error_rate, error_timestamps, final_node_error_max_time, node_latency)

                        loop_boolean == False
                        break

                    except:
                        logging.info("Error reading attribute")
                        message_end_timestamp = time.time()
                        logging.info(f"Message {num_messages} latency: {message_end_timestamp - message_start_timestamp}")
                        current_error_time = (message_end_timestamp - message_start_timestamp)
                        node_latency[i] += current_error_time
                        num_errors += 1
                        node_id_errors[i].append(num_messages)
                        node_error_rate[i] += 1
                        error_timestamps[num_messages] = [time_elapsed, current_time]

                        logging.info(f"Consecutive Errors: {consecutive_errors}")
                        logging.info(f"Consecutive Errors Current Value: {consecutive_errors[i]}")
                        if consecutive_errors[i] == True:
                            logging.info(f"Consecutive errors in node {i} detected!")
                        else:
                            node_error_max_time[i] = message_start_timestamp
                            logging.info(f"Starting error message timestamp {message_start_timestamp}")
                            consecutive_errors[i] = True
                     
                    num_messages += 1

                messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
                if num_messages % (len(self.all_dut_node_ids) * 10) == 0:
                    for node_id in self.all_dut_node_ids:
                        periodic_check_node_error_rate[node_id] = (node_error_rate.get(node_id) / messages_sent_per_device)
                        periodic_node_latency[node_id] = (node_latency.get(node_id) / messages_sent_per_device)

                    self.logging_statistics(time_elapsed, num_messages, num_errors, node_id_errors, node_error_rate, error_timestamps, final_node_error_max_time, node_latency, periodic_check_node_error_rate, periodic_node_latency, True)

                    if num_messages % 1000 == 0:
                        for key, value in error_timestamps.items():
                            logging.info(f"Error {key} Timestamps: {value}")
                
                logging.info("")
                time.sleep(.1)

        #When we force stop the test outside the device reading loop
        except Exception as e:
            logging.info(f"Test Ending because of: {e}")
            messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
            #Set Error Rate
            for node_id in self.all_dut_node_ids:
                node_error_rate[node_id] = (node_error_rate.get(node_id) / messages_sent_per_device)
            
            self.file_output(time_elapsed, num_messages, num_errors, node_id_errors, node_error_rate, error_timestamps, final_node_error_max_time, node_latency)
    
        
if __name__ == "__main__":
    default_matter_test_main()
