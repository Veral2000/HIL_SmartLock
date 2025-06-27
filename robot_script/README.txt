This is the RObot Framework Script, used to run the test cases on HIL Setup over Kafka Communication.

There are few commands that we need to run to perform the testing:

1. Start your HIL Setup and Kafka broker should running on HIL (pi@HIL)
2. Command to run specific test case "robot -d results --test "Test Case Name" serial.robot"
3. Command to run all test cases in sequence "robot -d results serial.robot" 
4. Results will be stored in Results folder.

Note: There is no need to run Kafka in Windows laptop, you should have kafka library in Python, also Eveything should be connected in local network (Same Network).
