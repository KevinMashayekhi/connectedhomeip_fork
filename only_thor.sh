#!/bin/sh
sudo service bluetooth restart
./scripts/tests/run_python_test.py --app-args "--discriminator 4081 4082 4083 4084 4085 4086 --KVS kvs1" --script "src/python_testing/testing_error_statistics.py" --script-args "--storage-path admin_storage.json --commissioning-method ble-thread --discriminator 4081 4082 4083 4084 4085 4086 --passcode 20202021 20202021 20202021 20202021 20202021 20202021 --dut-node-id 1 2 3 4 5 6 --thread-dataset-hex 0e08000000000001000035060004001fffe00708fd164ef2e2ac646e0410228a4bf817995a54dacd802af832138f0c0402a0f7f8000300001801025b2202085b22dead5b22beef03043562323205104c9bcdc6dc023344aca9d4baabfa90b8" --factoryreset | tee ../Documents/commissioning_logs_output/full_network_test.txt