import datetime, serial, sys, pexpect, argparse
from pexpect import fdpexpect
from time import sleep

def argParser(): #Function to pass arguments through command line
    parser = argparse.ArgumentParser()
    parser.add_argument("oFile", metavar="<path/filename*.log>", help="Output File (full path and name)")
    parser.add_argument("usbCon", metavar="</dev/ttyUSB*>", help="USB Connection (full path)")
    parser.add_argument("-t", "--tdm", dest="tdm", metavar="", help="run or no", default=None, choices=['run', 'just-test', 'none'])
    parser.add_argument("-e", "--e2e", dest="e2e", metavar="", help="run or no", default=None, choices=['run', 'just-test', 'none'])
    parser.add_argument("-d", "--dune", dest="dune", metavar="", help="start or none", default=None, choices=['start', 'none'])
    parser.add_argument("-c", "--temp", dest="temp", metavar="", help="check or none", default=None, choices=['check', 'none'])
    parser.add_argument("-m", "--memtest", dest="mem", metavar="", help="run or none", default=None, choices=['run', 'none'])
    args = parser.parse_args()
    main(args.usbCon, args.oFile, args.dune, args.tdm, args.temp, args.mem, args.e2e)

def main(usbCon, oFile, dune, tdm, temp, mem, e2e): #Main function
    username = input('Please enter your username: ')
    fd = serial.Serial(usbCon, 115200, timeout=1) #Connect to the Serial port
    ss = fdpexpect.fdspawn(fd, encoding='utf-8') #Opens the serial port as a child process
    ss.delaybeforesend = 5 #Delays sending commands
    logfile = open(oFile, "w")
    if ss.isalive():
        try:
            logfile.write("Connected to " + usbCon + '\n')
            logfile.write("DUNE started at: " + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + "\n")
            logfile.write("User: " + username + '\n')
            print("\nConnected to " + usbCon)
            print("DUNE started at: " + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            print("User: " + username  + "\n")
            if dune == "start":
                startDune(ss, logfile)
            if tdm == "run":
                tdmPythonPath = input('Please enter TDM Python script path: ')
                tdmTestPath = input('Please enter TDM Test script path: ')
                setEpp(ss, logfile)
                ss.close()
                tdmPython(ss, logfile, tdmPythonPath)
                tdmTest(ss, logfile, oFile, tdmTestPath, username)
            elif tdm == "just-test":
                tdmTestPath = input('Please enter TDM Test script path: ')
                tdmTest(ss, logfile, oFile, tdmTestPath, username)
            if e2e == "run":
                e2ePythonPath = input('Please enter End To End Python script path: ')
                e2eTestPath = input('Please enter End To End Test script path: ')
                setEpp(ss, logfile)
                ss.close()
                endToEnd(ss, logfile, e2ePythonPath)
                endToEndTest(ss, logfile, oFile, e2eTestPath, username)
            elif e2e == "just-test":
                e2eTestPath = input('Please enter End To End Test script path: ')
                endToEndTest(ss, logfile, oFile, e2eTestPath, username)
            if temp == "check":
                tempCheck(ss, logfile)
            if mem == "run":
                memtest(ss, logfile)
            logfile.close()
            ss.close()
        except KeyboardInterrupt:
            print("\nInterrupted manually.\nNOTE: Test might have not finished yet and logfile might not have written some of the results")

def startDune(ss, logfile): #Function to start DUNE
    logfile.write("Starting DUNE" + "\n")
    print("Starting DUNE" + "\n")
    ss.sendline('exit\r')
    ss.expect('buildroot login: ', timeout=None)
    ss.sendline('root')
    ss.expect('Password: ', timeout=3) #Uncomment this and the next line if DUNE also requires password
    ss.sendline('root') #Uncomment this and the previous line if DUNE also requires password
    ss.expect('#', timeout=None)
    logfile.write("Logged into DUNE\n")
    print("Logged into DUNE\n")

def setEpp(ss, logfile): #Function to set up EPP
    logfile.write("EPP setup is running, please wait...")
    print("EPP setup is running, please wait...")
    ss.sendline('/bin/sh -c "cd /opt/epp_debug_scripts/init_scripts/ && ./set_epp.sh"')
    ss.expect('Programmed Broadcast with src_mac 00:11:22:33:44:55 dst_mac 00:aa:bb:cc:dd:55', timeout=None)
    logfile.write("EPP is set\n")
    print('EPP is set\n')
    ss.close()

def tempCheck(ss, logfile): #Function to check the temperature
    i = int(input('Please enter the number of times you would love to check the Temperature: '))
    t = 0
    while t < i:
        ss.sendline('cd /root/')
        ss.expect('#', timeout=None)
        ss.sendline('./set_tsense.sh') #Make sure filename matches the one on your system
        ss.expect('#', timeout=None)
        ss.sendline('./tsense.sh') #Make sure filename matches the one on your system
        ss.expect('#', timeout=None)
        print("Checking the temperature:" + str(ss.before))
        logfile.write("\nChecking the temperature:" + str(ss.before))
        sleep(10)
        t += 1

def tdmPython(ss, logfile, tdmPythonPath): #Function to set TDM to send packets to the host device
    ss = pexpect.spawn(f'/bin/bash -c "cd {tdmPythonPath} && ./run_python.sh lb1"', encoding='utf-8')
    logfile.write("Running TDM Python script, please wait...")
    print("Running TDM Python script, please wait...")
    ss.delaybeforesend = 10 #Delays sending commands
    #ss.logfile_read = sys.stdout
    logfile.write("TDM Python script is done\n")
    print("TDM Python script is done\n")
    ss.expect(pexpect.EOF, timeout=None)
    ss.close()

def endToEnd(ss, logfile, e2ePythonPath): #Function to set E2E to send packets to the host device
    ss = pexpect.spawn(f'/bin/bash -c "cd {e2ePythonPath} && ./run_python.sh lb1 c71_0"', encoding='utf-8')
    logfile.write("Running End To End Python script, please wait...")
    print("Running End To End Python script, please wait...")
    ss.delaybeforesend = 10 #Delays sending commands
    ss.sendline('\n\n\n')
    ss.logfile_read = sys.stdout
    logfile.write("\nEnd To End Python script is done\n")
    print("\nEnd To End Python script is done\n")
    ss.expect(pexpect.EOF, timeout=None)
    ss.close()

def endToEndTest(ss, logfile, oFile, e2eTestPath, username):
    ss = pexpect.spawn('/bin/bash', encoding='utf-8')
    ss.delaybeforesend = 3
    ss.sendline(f'cd {e2eTestPath}')
    ss.sendline(f'./run_test_time_0.sh 1 1 1 1 100000000 {oFile} 5 0')
    ss.expect(f'{username}*', timeout=None)
    print("\n\nEnd To End Test is running, please wait until it's done\n")
    ss.close()
    while True:
        command = "ps -ef | grep proc_rx"
        ss = pexpect.spawn(f'/bin/bash -c "{command}"', encoding='utf-8')
        ss.expect(pexpect.EOF, timeout=None)
        if "enp1s0f0" in ss.before:
            command = f"grep -A 2 'do compare' {e2eTestPath}*/{oFile}* | grep mis | wc"
            ss = pexpect.spawn(f'/bin/bash -c "{command}"', encoding='utf-8')
            ss.expect(pexpect.EOF, timeout=None)
            print("Mismatch count: ", end='')
            print(ss.before)
            ss.close()
            sleep(60)
        else:
            ss = pexpect.spawn(f'/bin/bash -c "tail {e2eTestPath}*/{oFile}*"', encoding='utf-8')
            ss.expect(pexpect.EOF, timeout=None)
            logfile.write(str(ss.before))
            print("\nTest ended")
            break

def tdmTest(ss, logfile, oFile, tdmTestPath, username):
    ss = pexpect.spawn('/bin/bash', encoding='utf-8')
    ss.delaybeforesend = 3
    ss.sendline(f'cd {tdmTestPath}')
    ss.sendline(f'./run_test_time_1.sh 0 0 0 0 100000000 {oFile} 30 0 1')
    ss.expect(f'{username}*', timeout=None)
    print("\n\nTDM Test is running, please wait until it's done\n")
    ss.close()
    while True:
        command = "ps -ef | grep proc_rx"
        ss = pexpect.spawn(f'/bin/bash -c "{command}"', encoding='utf-8')
        ss.expect(pexpect.EOF, timeout=None)
        if "proc_rx.capt" in ss.before:
            command = f"grep -A 2 'do compare' {tdmTestPath}logs/{oFile}* | grep mis | wc"
            ss = pexpect.spawn(f'/bin/bash -c "{command}"', encoding='utf-8')
            ss.expect(pexpect.EOF, timeout=None)
            print("Mismatch count: ", end='')
            print(ss.before)
            ss.close()
            sleep(60)
        else:
            ss = pexpect.spawn(f'/bin/bash -c "tail {tdmTestPath}logs/{oFile}*"', encoding='utf-8')
            ss.expect(pexpect.EOF, timeout=None)
            logfile.write(str(ss.before))
            print("\nTest ended")
            break

def memtest(ss, logfile): #Function to start Memtester
    ss.sendline('./memtest') #Make sure filename matches the one on your system
    ss.expect('#', timeout=None)
    print('Memtester is running...\nPlease wait until test is done\n')
    while True:
        ss.sendline('ps | grep memtest') #checks the running memtester processes
        ss.expect('#', timeout=None)
        if 'memtester' not in ss.before:
            ss.sendline('ls -la log/')
            ss.expect('#', timeout=None)
            print("Memtest results: \n" + str(ss.before))
            logfile.write("Memtest results: \n" + str(ss.before))
            ss.close()
            break
        else:
            sleep(10)

argParser() #Calling the Argument Passer function to start executing
