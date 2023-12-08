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

        node_id_errors = {key: [] for key in self.all_dut_node_ids}
        node_error_rate = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        temp_node_error_rate = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        node_error_max_time = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        final_node_error_max_time = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        node_latency = dict(zip(self.all_dut_node_ids, [0]*len(self.all_dut_node_ids)))
        consecutive_errors = False

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

                    try:
                        attribute_state = await dev_ctrl.ReadAttribute(i, [Clusters.OnOff])
                        node_latency[i] += ((time.time() - start_time) - time_elapsed)
                        #if final_node_error_max_time[i] < node_error_max_time[i]:
                        #    final_node_error_max_time[i] = node_error_max_time[i]
                        #node_error_max_time[i] = 0
                        #consecutive_errors = False

                    except KeyboardInterrupt:
                        messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
                        #Set Error Rate
                        for i in self.all_dut_node_ids:
                            node_error_rate[i] = (node_error_rate.get(i) / messages_sent_per_device)
                            node_latency[i] = (node_latency[i] / messages_sent_per_device)
                        logging.info("Network Test Statistics")
                        logging.info("********************************************************************")
                        logging.info(f"Total number of messages sent in network: {num_messages}")
                        logging.info(f"Total number of error messages in network: {num_errors}")
                        logging.info("")
                        for key, value in node_id_errors.items():
                            logging.info(f"Node {key} errors: {value} ")
                        logging.info("")
                        for key, value in node_error_rate.items():
                            logging.info(f"Node {key} Error Rate: {value}")
                        logging.info("")
                        for key, value in error_timestamps.items():
                            logging.info(f"Error {key} Timestamps: {value}")
                        for key, value in final_node_error_max_time.items():
                            logging.info(f"Node {key} max synchronization loss duration: {value}\n")
                        for key, value in node_latency.items():
                            logging.info(f"Node {key} average latency: {value}\n")
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
                        current_error_time = time.time() - time_elapsed
                        num_errors += 1
                        node_id_errors[i].append(num_messages)
                        node_error_rate[i] += 1
                        error_timestamps[num_messages] = [time_elapsed, current_time]

                        if consecutive_errors == True:
                            node_error_max_time[i] += current_error_time
                            logging.info(f"Node {i} curent sync loss time: {node_error_max_time[i]}")
                        else:
                            node_error_max_time[i] = current_error_time
                            logging.info(f"Error Detected, {node_error_max_time}")
                            consecutive_errors = True
                     
                    num_messages += 1

                messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
                if num_messages % 100 == 0:
                    for i in self.all_dut_node_ids:
                        temp_node_error_rate[i] = (node_error_rate.get(i) / messages_sent_per_device)
                    logging.info(f"Time Elapsed: {time_elapsed}")
                    logging.info(f"Total number of messages sent in network: {num_messages}")
                    logging.info(f"Total number of error messages in network: {num_errors}")
                    for key, value in node_id_errors.items():
                        logging.info(f"Node {key} errors: {value} ")
                    logging.info("")
                    for key, value in temp_node_error_rate.items():
                        logging.info(f"Node {key} Error Rate: {value}")
                    logging.info("")
                    if num_messages % 1000 == 0:
                        for key, value in error_timestamps.items():
                            logging.info(f"Error {key} Timestamps: {value}")

                time.sleep(1)

        except KeyboardInterrupt:
            messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
            #Set Error Rate
            for i in self.all_dut_node_ids:
                node_error_rate[i] = (node_error_rate.get(i) / messages_sent_per_device)#(1-((messages_sent_per_device - node_error_rate.get(i)) / messages_sent_per_device))
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
    
        #Attribute Reading
        #while (time.time() - start_time) < run_time:
        ##user_input = input("Enter 1 to read attribute, enter anything else to quit")
        ##while user_input == "1":
        #    #for i in range(1,4):
        #    for i in self.all_dut_node_ids:
        #        time_elapsed = time.time() - start_time
        #        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-5]
        #        logging.info(f"Time Elapsed: {time_elapsed}")
        #        logging.info(f"MessageID: {num_messages}")
        #        logging.info(f"Reading attribute for node {i}:")

        #        try:
        #            lock_state = await dev_ctrl.ReadAttribute(i, [Clusters.DoorLock.Attributes.LockState])
        #        except:
        #            logging.info("Error reading attribute")
        #            num_errors += 1
        #            node_id_errors[i].append(num_messages)
        #            node_error_rate[i] += 1
        #            error_timestamps[num_messages] = [time_elapsed, current_time]
        #       
        #        num_messages += 1

        #    messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
        #    if num_messages % 100 == 0:
        #        for i in self.all_dut_node_ids:
        #            temp_node_error_rate[i] = (node_error_rate.get(i) / messages_sent_per_device)
        #        logging.info(f"Total number of messages sent in network: {num_messages}")
        #        logging.info(f"Total number of error messages in network: {num_errors}")
        #        for key, value in node_id_errors.items():
        #            logging.info(f"Node {key} errors: {value} ")
        #        logging.info("")
        #        for key, value in temp_node_error_rate.items():
        #            logging.info(f"Node {key} Error Rate: {value}")
        #        logging.info("")
        #        if num_messages % 1000 == 0:
        #            for key, value in error_timestamps.items():
        #                logging.info(f"Error {key} Timestamps: {value}")

        #    time.sleep(1)
        ##    user_input = input("Enter 1 to read attribute, enter anything else to quit")

        #messages_sent_per_device = (num_messages / (len(self.all_dut_node_ids)))
        ##Set Error Rate
        #for i in self.all_dut_node_ids:
        #    node_error_rate[i] = (node_error_rate.get(i) / messages_sent_per_device)#(1-((messages_sent_per_device - node_error_rate.get(i)) / messages_sent_per_device))
       
        #logging.info("Network Test Statistics")
        #logging.info("********************************************************************")
        #logging.info(f"Total number of messages sent in network: {num_messages}")
        #logging.info(f"Total number of error messages in network: {num_errors}")
        #logging.info("")
        #for key, value in node_id_errors.items():
        #    logging.info(f"Node {key} errors: {value} ")
        #logging.info("")
        #for key, value in node_error_rate.items():
        #    logging.info(f"Node {key} Error Rate: {value}")
        #logging.info("")
        #for key, value in error_timestamps.items():
        #    logging.info(f"Error {key} Timestamps: {value}")
        #logging.info("********************************************************************")


if __name__ == "__main__":
    default_matter_test_main()
