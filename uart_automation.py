import datetime, serial, sys, pexpect, argparse
from pexpect import fdpexpect
from time import sleep

def argParser(): #Function to pass arguments through command line
    parser = argparse.ArgumentParser()
    parser.add_argument("oFile", metavar="<path/filename*.log>", help="Output File (full path and name)")
    parser.add_argument("usbConMcu", metavar="</dev/ttyUSB*>", help="USB Connection for MCU(full path)")
    parser.add_argument("usbConLinux", metavar="</dev/ttyUSB*>", help="USB Connection for Linux(full path)")
    parser.add_argument("-cm", "--margin", dest="margin", metavar="", help="nominal, high, low, none", default='nominal', choices=['nominal', 'high', 'low', 'none'])
    parser.add_argument("-p", "--power", dest="power", metavar="", help="on, off, unforce, none", default=None, choices=['on', 'off', 'unforce', 'none'])
    parser.add_argument("-m", "--memtest", dest="mem", metavar="", help="run, run-all or none", default=None, choices=['run', 'run-all', 'none'])
    parser.add_argument("-t", "--temp", dest="temp", metavar="", help="check or none", default=None, choices=['check', 'none'])
    parser.add_argument("-ht", "--horta", dest="horta", metavar="", help="start or none", default=None, choices=['start', 'none'])
    args = parser.parse_args()
    horta_mcu(args.oFile, args.usbConMcu, args.margin, args.power, args.usbConLinux)
    horta_linux(args.temp, args.mem, args.usbConLinux, args.oFile, args.horta, args.usbConMcu)

###########################################################################################################################################################

# Horta MCU

###########################################################################################################################################################

def horta_mcu(oFile, usbConMcu, margin, power, usbConLinux):
    mcu = serial.Serial(f"/dev/tty{usbConMcu}", 57600, timeout=1) #Connect to the Serial port
    sleep(0.1)
    if mcu.isOpen():
        global logfile
        logfile = open(oFile, "w") #Create a log to dump Horta's log
        logfile.write(f'Horta started at: {str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}\n')
        logfile.write(f'Connected to {format(mcu.port)}\n\n')
        print(f'Horta started at: {str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}')
        print(f'Connected to {format(mcu.port)}\n')
        try:
            mcu.write(b"0\r") #Makes sure to start from beginning
            sleep(0.1)
            mcu.flushInput()
            powerSelect(mcu, logfile, power, usbConLinux)
            readHorta(mcu, logfile)
            marginSelect(mcu, margin, logfile)
            readHorta(mcu, logfile)
            print('Current measure before:')
            logfile.write('Current measure before:\n')
            currentMeasure(mcu, logfile)
            readHorta(mcu, logfile)     
            #mcu.close()
        except KeyboardInterrupt:
            print("\nInterrupted manually.\nNOTE: Test might have not finished yet and logfile might not have written some of the results")
            sys.exit(0)
            

#Function to return to root, used in every function
def powDir(mcu):
    mcu.write(b"0\r") #Make sure to start from beginning
    sleep(0.1)
    mcu.write(b"pow\r")
    sleep(0.1)

#Function to choose power state
def powerSelect(mcu, logfile, power, usbConLinux):
    if power == "on":
        powDir(mcu)
        mcu.write(b"force\r") #Change to force
        sleep(0.5)
        mcu.write(b"fh_newpw\r") #Force switches horta board on
        print('Power force-switched on\n') #Prints to show power switched on
        fd = serial.Serial(("/dev/tty" + usbConLinux), 115200, timeout=1) #Connect to the Serial port
        hortaLinux = fdpexpect.fdspawn(fd, encoding='utf-8') #Opens the serial port as a child process
        hortaLinux.delaybeforesend = 5 #Delays sending commands
        hortaLinux.logfile_read = sys.stdout
        hortaLinux.expect("INFO:    Configure QSPI0 MM")
        hortaLinux.logfile_read = sys.stdout
        hortaLinux.expect("INFO:    Using crypto library 'mbed TLS'")
        string1 = str(hortaLinux.before)
        string1 = string1.replace('NOTICE:  ', "")
        logfile.write(f'BL2 Ver.:\n{string1}\n')
        hortaLinux.logfile_read = sys.stdout
        hortaLinux.expect("Trying 'kernel@0' kernel subimage")
        hortaLinux.logfile_read = sys.stdout
        hortaLinux.expect('Type:         Kernel Image')
        string1 = str(hortaLinux.before)
        string1 = string1.replace('     ', "")
        logfile.write(f'Linux Ver.:\n{string1}\n')
        hortaLinux.logfile_read = sys.stdout
        hortaLinux.expect('buildroot login:', timeout=None)
        print('\n')
        hortaLinux.close()
        logfile.write('Power force-switched on\n\n')
        sleep(2)
        print("Power State: ", end="")    
        logfile.write("Power State: ")    
        sleep(1)
        mcu.write(b"0\r") #Make sure to start from beginning
        sleep(0.5)
        mcu.write(b"pw_state\r") #Shows Power State
        mcu.flushInput()
        sleep(1)
    elif power == "off":
        powDir(mcu)
        mcu.write(b"force\r") #Change to force
        sleep(0.5)
        mcu.write(b"fl_newpw\r") #Forceswitches horta board off
        logfile.write('Power force-switched off\n\nExiting the script\n')
        print('Power force-switched off\nExiting the script\n') #Prints to show power switched off
        mcu.close()
        sys.exit()
    elif power == "unforce":
        powDir(mcu)
        mcu.write(b"force\r") #Change to force
        sleep(0.5)
        mcu.write(b"cr_newpw\r") #Unforces the device to the physical switches state
        logfile.write('Power state unforced\n\n')
        print('Power power state unforced\n') #Prints to show power state unforced
        sleep(2)
        print("Power State: ", end="")    
        logfile.write("Power State: ")    
        sleep(1)
        mcu.write(b"0\r") #Make sure to start from beginning
        sleep(0.5)
        mcu.write(b"pw_state\r") #Shows Power State
        mcu.flushInput()
        sleep(1)

#Function to choose Margin state
def marginSelect(mcu, margin, logfile):
    powDir(mcu)
    mcu.write(b"vout\r") #Changes directory to vout
    sleep(0.1)
    if margin == "nominal":
        mcu.write(b"ALL_TYP\r") #Changes Margin to Typical
        sleep(1)
        logfile.write('Margin: Nominal\n')
        print('Magin: Nominal') #Prints to show selected Margin
    elif margin == "high":
        mcu.write(b"ALL_MAX\r") #Changes Margin to High
        sleep(1)
        logfile.write('Margin: High\n')
        print('Magin: High') #Prints to show selected Margin
    elif margin == "low":
        mcu.write(b"ALL_MIN\r") #Changes Margin to Low
        sleep(1)
        logfile.write('Margin: Low\n')
        print('Magin: Low') #Prints to show selected Margin
    elif margin == None or margin == "none":
        logfile.write("Margin state remains, see status below\n")
        print("Margin state remains, see status below")
    sleep(1)
    mcu.flushInput()

#Fucntion to show Current Measurement
def currentMeasure(mcu, logfile):
    powDir(mcu)
    mcu.write(b"cm\r") #Prints Current Measurement status
    mcu.flushInput()
    print('Showing Current Measurement: ', end='')
    logfile.write('Showing Current Measurement: ') 
    sleep(2.2)

#Function to read and write from Horta
def readHorta(mcu, logfile):
    status = mcu.read(mcu.inWaiting())
    status = str(status, 'utf-8')
    status = status.replace("\r\n","\n")
    logfile.write(status + "\n")
    print(status)
    if "current_power_state : 0" in status:
        sys.exit()

###########################################################################################################################################################

# Horta Linux

###########################################################################################################################################################

def copy(hortaLinux):
    command = f"cd /share/mirhadi.seyidli/scripts && cat tsense.sh"
    ls = pexpect.spawn(f'/bin/bash -c "{command}"', encoding='utf-8')
    ls.expect(pexpect.EOF, timeout=None)
    print(ls.before)
    hortaLinux.sendline(f"{ls.before}")
    hortaLinux.expect(pexpect.EOF, timeout=None)
    command = f"cd /share/mirhadi.seyidli/scripts && cat max_tsense.sh"
    ls = pexpect.spawn(f'/bin/bash -c "{command}"', encoding='utf-8')
    ls.expect(pexpect.EOF, timeout=None)
    print(ls.before)
    hortaLinux.sendline(f"{ls.before}")
    hortaLinux.expect(pexpect.EOF, timeout=None)
    command = f"cd /share/mirhadi.seyidli/scripts && cat memtest"
    ls = pexpect.spawn(f'/bin/bash -c "{command}"', encoding='utf-8')
    ls.expect(pexpect.EOF, timeout=None)
    print(ls.before)
    hortaLinux.sendline(f"{ls.before}")
    hortaLinux.expect(pexpect.EOF, timeout=None)
    command = f"cd /share/mirhadi.seyidli/scripts && cat directories"
    ls = pexpect.spawn(f'/bin/bash -c "{command}"', encoding='utf-8')
    ls.expect(pexpect.EOF, timeout=None)
    print(ls.before)
    hortaLinux.sendline(f"{ls.before}")
    hortaLinux.expect(pexpect.EOF, timeout=None)
    hortaLinux.sendline('chmod 777 *')
    hortaLinux.expect(pexpect.EOF, timeout=None)
    ls.logfile_read = sys.stdout
    hortaLinux.logfile_read = sys.stdout

def horta_linux(temp, mem, usbConLinux, oFile, horta, usbConMcu):
    fd = serial.Serial(("/dev/tty" + usbConLinux), 115200, timeout=1) #Connect to the Serial port
    hortaLinux = fdpexpect.fdspawn(fd, encoding='utf-8') #Opens the serial port as a child process
    hortaLinux.delaybeforesend = 5 #Delays sending commands
    if hortaLinux.isalive():
        try:
            logfile.write(f'Connected to /dev/tty{usbConLinux}\n')
            print(f'Connected to /dev/tty{usbConLinux}\n')
            if horta == "start":
                hortaLogin(hortaLinux, logfile)
            if temp == "check":
                tempCheck(hortaLinux, logfile)
            if mem == "run-all":
                copy(hortaLinux)
                global margin1
                n = int(input("Please enter the size of the memtest you would love to run: "))
                m = int(input("Please enter the number of loops you would love to run the test: "))
                board = input("Please enter the board number: ")
                logfile.write(f"Board: {board}\n")
                chip = input("Please enter the chip name: ")
                logfile.write(f"Chip: {chip}\n")
                powerMeasure = input("Please enter the power: ")
                logfile.write(f"Power: {powerMeasure}W AC\n")
                mcu = serial.Serial(f"/dev/tty{usbConMcu}", 57600, timeout=1) #Connect to the Serial port
                margin1 = "nominal"
                margin = margin1
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                margin1 = "high"
                margin = margin1
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                margin1 = "low"
                margin = margin1
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                hortaLinux.close()
            elif mem == 'run':
                copy(hortaLinux)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                hortaLinux.close()
        except KeyboardInterrupt:
            print("\nInterrupted manually.\nNOTE: Test might have not finished yet and logfile might not have written some of the results")
            sys.exit(0)

def hortaLogin(hortaLinux, logfile):
    #hortaLinux.sendline('root')
    #hortaLinux.expect('Password: ', timeout=None) #Uncomment this and the next line if DUNE also requires password
    hortaLinux.sendline('root') #Uncomment this and the previous line if DUNE also requires password
    hortaLinux.expect('#', timeout=5)
    print("Logged into Horta\n")

def tempCheck(hortaLinux, logfile): #Function to check the temperature
        hortaLinux.sendline('cd /root/')
        hortaLinux.expect('#', timeout=None)
        hortaLinux.sendline('./tsensse.sh') #Make sure filename matches the one on your system
        hortaLinux.expect('#', timeout=None)
        print("Checking the temperature:" + str(hortaLinux.before))
        logfile.write("\nChecking the temperature:" + str(hortaLinux.before))

def memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m): #Function to start Memtester
    hortaLinux.sendline(f'./memtest {n} {m}') #Make sure filename matches the one on your system
    hortaLinux.expect('#', timeout=None)
    i = 0
    w = 100
    hortaLinux.logfile_read = sys.stdout
    print("\nMemtester is running. Please wait until it's done.\n")
    while True:
        mcu = serial.Serial(f"/dev/tty{usbConMcu}", 57600, timeout=1) #Connect to the Serial port
        status = mcu.read(mcu.inWaiting())
        status = str(status, 'utf-8')
        status = status.replace("\r\n","\n")
        if "power not good is occured" in status:
            logfile.write(status + "\n")
            print(status)
            print("\n--- Kernel Panic ---\n")
            mcu.close()
        else:
            powDir(mcu)
            mcu.write(b"cm\r") #Prints Current Measurement status
            mcu.flushInput()
            print('Showing Current Measurement: ', end='')
            sleep(2.2)
            status = mcu.read(mcu.inWaiting())
            status = str(status, 'utf-8')
            status = status.replace("\r\n","\n")
            print(status)
        hortaLinux.sendline('ps | grep memtest') #checks the running memtester processes
        hortaLinux.expect('#', timeout=None)
        string2 = str(hortaLinux.before)
        if "panic" in string2.lower() or "kernel" in string2.lower() or "horta" in string2.lower() or "end" in string2.lower() or "trace" in string2.lower() or "cpu" in string2.lower():
            print("\n\n--- Kernel Panic ---\n\n")
            logfile.write("\n--- Kernel Panic ---\n")
            powDir(mcu)
            mcu.write(b"force\r") #Change to force
            sleep(0.5)
            mcu.write(b"fl_newpw\r") #Forceswitches horta board off
            logfile.write('Power force-switched off\n\nRestarting Horta\n')
            print('Power force-switched off\nRestarting Horta\n') #Prints to show power switched off
            powDir(mcu)
            mcu.write(b"force\r") #Change to force
            sleep(0.5)
            mcu.write(b"fh_newpw\r") #Force switches horta board on
            print('Power force-switched on\n') #Prints to show power switched on
            hortaLinux.logfile_read = sys.stdout
            hortaLinux.expect('buildroot login:', timeout=None)
            hortaLogin(hortaLinux, logfile)
            copy(hortaLinux)
            if margin1 == "nominal":
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                margin = "high"
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                margin = "low"
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                hortaLinux.close()
            elif margin1 == "high":
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                margin = "low"
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                hortaLinux.close()
            elif margin1 == "low":
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                hortaLinux.close()
            sys.exit(0)
        if 'memtester' not in hortaLinux.before: #Prints results
            currentMeasure(mcu, logfile)
            readHorta(mcu, logfile)
            hortaLinux.sendline('ls -ltr logs/')
            hortaLinux.expect('#', timeout=None)
            logfile.write("Memtest results: \n" + str(hortaLinux.before))
            print(hortaLinux.before)
            hortaLinux.sendline('./tsense.sh') #Make sure filename matches the one on your system
            hortaLinux.expect('#', timeout=None)
            print("Final temperature check:" + str(hortaLinux.before))
            logfile.write(f"Final temperature check: {str(hortaLinux.before)}\n")
            break
        else:
            warning(hortaLinux, usbConMcu, usbConLinux, oFile) #run warning script for safety
            if i == w:
                print("Memtester is still running. Please wait until it's done")
                hortaLinux.sendline('ls -ltr logs/')
                hortaLinux.expect('#', timeout=None)
                print(hortaLinux.before)
                hortaLinux.sendline('./tsense.sh') #Make sure filename matches the one on your system
                hortaLinux.expect('#', timeout=None)
                print("Checking the temperature:" + str(hortaLinux.before))
                logfile.write(f"Checking the temperature: {str(hortaLinux.before)}\n")
                w += 100
            elif i != w:
                i += 1

def warning(hortaLinux, usbConMcu, usbConLinux, oFile):
    hortaLinux.sendline('./max_tsense.sh') #Make sure filename matches the one on your system
    hortaLinux.expect('#', timeout=None)
    string = str(hortaLinux.before) #Extracts the max temperature
    if "random: crng init done" not in string:
        string = string.replace("./max_tsense.sh", "")
        string = string.replace("max temp: ", "")
        string = string.replace("C", "")
        if float(string) > 120 and float(string) < 124: #If the temperature is in range of danger, prints a warning
            print("Warning temperature is getting too high!!!")
            sleep(10)
        elif float(string) >= 124: #If temperature is higher than damage range, powers down the board
            hortaLinux.close()
            print("Temperature is too high! Shutting down Horta!")
            ss = pexpect.spawn(f'python3 horta.py {oFile} /dev/tty{usbConMcu} /dev/tty{usbConLinux} -p off')
            ss.expect(pexpect.EOF, timeout=None)
            sys.exit()

argParser() #Calling the Argument Passer function to start executing
sys.exit(0)
