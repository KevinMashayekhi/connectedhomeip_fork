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

class large_network(MatterBaseTest):
    @async_test_body
    async def test_large_network(self):
        file = open("error_statistics.txt", "w")
        dev_ctrl = self.default_controller
        logging.info("Commissioning is complete")
        #logging.info("60 second delay to give FTD time to setup")
        #time.sleep(50)
        #logging.info("10 seconds remaining")
        #time.sleep(10)
        logging.info("Attempting to read attributes")
        logging.info(f"All node ids: {self.all_dut_node_ids}")
        logging.info("-------------------------------------------------------------------------")
        #logging.info(f"Attributes of Clusters: {dir(Clusters)}")
        #logging.info(f"Attributes of door lock: {dir(Clusters.DoorLock)}")
        #logging.info(f"Attributes of door lock attributes: {dir(Clusters.DoorLock.Attributes)}")
        #logging.info(f"Attributes of door lock commands: {dir(Clusters.DoorLock.Commands)}")
        #logging.info(f"dev_ctrl: {dir(dev_ctrl)}")

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
        #Boolean dictionary for if we have back to back errors for that node, used to determine if we should start calcuating the error synchronization loss for the current node
        consecutive_errors = dict(zip(self.all_dut_node_ids, [False]*len(self.all_dut_node_ids)))
        #Contains the previous failed message timestamp (taken from after we know it has failed)
        node_failed_message_timestamp = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))

        error_timestamps = {}
        num_messages = 0
        num_errors = 0
        loop_boolean = True
        #run_time = 300
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
                        node_latency[i] += (message_end_timestamp - message_start_timestamp)
                        if final_node_error_max_time[i] < node_error_max_time[i]:
                            final_node_error_max_time[i] = node_error_max_time[i]
                        node_error_max_time[i] = 0
                        consecutive_errors = False

                    except KeyboardInterrupt:
                        messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
                        #Set Error Rate
                        for node_id in self.all_dut_node_ids:
                            node_error_rate[node_id] = (node_error_rate.get(node_id) / messages_sent_per_device)
                            logging.info(f"Node {node_id} total latency {node_latency[node_id]}")
                            node_latency[node_id] = (node_latency[node_id] / messages_sent_per_device)
                        logging.info("Network Test Statistics")
                        logging.info("********************************************************************")
                        logging.info(f"Total number of messages sent in network: {num_messages}")
                        logging.info(f"Total number of error messages in network: {num_errors}")
                        logging.info("")
                        for key, value in node_id_errors.items():
                            logging.info(f"Node {key} errors: {value}")
                        logging.info("")
                        for key, value in node_error_rate.items():
                            logging.info(f"Node {key} Error Rate: {value}")
                        logging.info("")
                        for key, value in error_timestamps.items():
                            logging.info(f"Error {key} Timestamps: {value}")
                        logging.info("")
                        for key, value in final_node_error_max_time.items():
                            logging.info(f"Node {key} max synchronization loss duration: {value}")
                        logging.info("")
                        for key, value in node_latency.items():
                            logging.info(f"Node {key} average latency: {value}")
                        logging.info("********************************************************************")

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
                        loop_boolean == False
                        break

                    except:
                        logging.info("Error reading attribute")
                        message_end_timestamp = time.time()
                        node_latency[i] += (message_end_timestamp - message_start_timestamp)
                        current_error_time = time.time() - time_elapsed
                        num_errors += 1
                        node_id_errors[i].append(num_messages)
                        node_error_rate[i] += 1
                        error_timestamps[num_messages] = [time_elapsed, current_time]

                        if consecutive_errors == True:
                            node_error_max_time[i] += current_error_time
                            logging.info(f"Node {i} current sync loss time: {node_error_max_time[i]}")
                        else:
                            node_error_max_time[i] = current_error_time
                            logging.info(f"Error Detected, {node_error_max_time}")
                            consecutive_errors = True
                     
                    num_messages += 1

                messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
                if num_messages % 100 == 0:
                    for node_id in self.all_dut_node_ids:
                        periodic_check_node_error_rate[node_id] = (node_error_rate.get(node_id) / messages_sent_per_device)
                    logging.info(f"Time Elapsed: {time_elapsed}")
                    logging.info(f"Total number of messages sent in network: {num_messages}")
                    logging.info(f"Total number of error messages in network: {num_errors}")
                    for key, value in node_id_errors.items():
                        logging.info(f"Node {key} errors: {value}")
                    logging.info("")
                    for key, value in periodic_check_node_error_rate.items():
                        logging.info(f"Node {key} Error Rate: {value}")
                    logging.info("")
                    for key, value in error_timestamps.items():
                        logging.info(f"Error {key} Timestamps: {value}")
                    logging.info("")
                    for key, value in final_node_error_max_time.items():
                        logging.info(f"Node {key} max synchronization loss duration: {value}")
                    logging.info("")
                    for key, value in node_latency.items():
                        logging.info(f"Node {key} average latency: {value}")
                    
                    if num_messages % 1000 == 0:
                        for key, value in error_timestamps.items():
                            logging.info(f"Error {key} Timestamps: {value}")

                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("This is the outer exception catch block")
            messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
            #Set Error Rate
            for node_id in self.all_dut_node_ids:
                node_error_rate[node_id] = (node_error_rate.get(node_id) / messages_sent_per_device)
            file.write("Network Test Statistics \n")
            file.write("******************************************************************** \n")
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
                file.write("Node {0} average latency {1}\n".format(key,value))
    
        
if __name__ == "__main__":
    default_matter_test_main()
