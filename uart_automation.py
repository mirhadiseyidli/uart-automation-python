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
    parser.add_argument("-t", "--temp", dest="temp", metavar="", help="-50 < i < 150", default=None)
    parser.add_argument("-ht", "--horta", dest="horta", metavar="", help="start or none", default=None, choices=['start', 'none'])
    parser.add_argument("-cp", "--copy", dest="copy", metavar="", help="copy or none", default=None, choices=['copy', 'none'])
    args = parser.parse_args()
    horta_mcu(args.oFile, args.usbConMcu, args.margin, args.power, args.usbConLinux, args.mem, args.temp)
    horta_linux(args.temp, args.mem, args.usbConLinux, args.oFile, args.horta, args.usbConMcu, args.copy)

def horta_mcu(oFile, usbConMcu, margin, power, usbConLinux, mem, temp):
    mcu = serial.Serial(f"/dev/tty{usbConMcu}", 57600, timeout=1) #Connect to the Serial port
    sleep(0.1)
    if mcu.isOpen():
        global logfile
        logfile = open(oFile, "w") #Create a log to dump Horta's log
        logfile.write(f'Horta started at: {str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}\n')
        logfile.write(f'Connected to {format(mcu.port)}\n\n')
        print(f'Horta started at: {str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}')
        print(f'Connected to {format(mcu.port)}\n')
        global n
        global m
        if power != "off":
            board = input("Please enter the board number: ")
            logfile.write(f"Board: {board}\n")
            chip = input("Please enter the chip name: ")
            logfile.write(f"Chip: {chip}\n")
            if mem == "run" or mem == "run-all":
                n = int(input("Please enter the size of the memtest you would love to run: "))
                m = int(input("Please enter the number of loops you would love to run the test: "))
        try:
            mcu.write(b"0\r") #Makes sure to start from beginning
            sleep(0.1)
            mcu.flushInput()
            powerSelect(mcu, logfile, power, usbConLinux, temp)
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
def powerSelect(mcu, logfile, power, usbConLinux, temp):
    if power == "on":
        powDir(mcu)
        mcu.write(b"force\r") #Change to force
        sleep(0.5)
        mcu.write(b"fh_newpw\r") #Force switches horta board on
        print('Power force-switched on\n') #Prints to show power switched on
        buildKernelVer(usbConLinux)
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
        if temp == "off":
            cc = pexpect.spawn(f'python3 ThermalMachine3.py 10.1.0.3 -p off', encoding='utf-8')
            cc.expect(pexpect.EOF, timeout=None)
            cc.close()
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

def buildKernelVer(usbConLinux):
    fd = serial.Serial(("/dev/tty" + usbConLinux), 115200, timeout=1) #Connect to the Serial port
    hortaLinux = fdpexpect.fdspawn(fd, encoding='utf-8') #Opens the serial port as a child process
    hortaLinux.delaybeforesend = 5 #Delays sending commands
    hortaLinux.logfile_read = sys.stdout
    #hortaLinux.expect("INFO:    Configure QSPI0 MM") #Uncomment if QSPI mode
    hortaLinux.expect("INFO:    Configure eMMC") #Uncomment if eMMC mode
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

#Function to choose Margin state
def marginSelect(mcu, margin, logfile):
    powDir(mcu)
    mcu.write(b"vout\r") #Changes directory to vout
    sleep(0.1)
    if margin == "nominal":
        mcu.write(b"ALL_TYP\r") #Changes Margin to Typical
        sleep(1)
        logfile.write('Margin: Nominal\n')
        print('\nMagin: Nominal') #Prints to show selected Margin
    elif margin == "high":
        mcu.write(b"ALL_MAX\r") #Changes Margin to High
        sleep(1)
        logfile.write('Margin: High\n')
        print('\nMagin: High') #Prints to show selected Margin
    elif margin == "low":
        mcu.write(b"ALL_MIN\r") #Changes Margin to Low
        sleep(1)
        logfile.write('Margin: Low\n')
        print('\nMagin: Low') #Prints to show selected Margin
    elif margin == None or margin == "none":
        logfile.write("Margin state remains, see status below\n")
        print("\nMargin state remains, see status below")
    sleep(1)
    mcu.flushInput()

#Fucntion to show Current Measurement
def currentMeasure(mcu, logfile):
    powDir(mcu)
    mcu.write(b"cm\r") #Prints Current Measurement status
    mcu.flushInput()
    print('Showing Current Measurement: ', end='')
    logfile.write('Showing Current Measurement: ') 
    sleep(2.5)

#Function to read and write from Horta
def readHorta(mcu, logfile):
    status = mcu.read(mcu.inWaiting())
    status = str(status, 'utf-8')
    status = status.replace("\r\n","\n")
    logfile.write(status + "\n")
    print(status)
    if "current_power_state : 0" in status:
        sys.exit()

def copyFiles(hortaLinux): #For QSPI Images that lose all scripts every power cycle
    command = "mkdir logs"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "touch logs/00.log logs/00_err.log"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "touch logs/01.log logs/01_err.log"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "touch logs/1.log logs/1_err.log"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "touch logs/2.log logs/2_err.log"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "touch logs/3.log logs/3_err.log"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "touch logs/4.log logs/4_err.log"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "touch logs/5.log logs/5_err.log"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "touch logs/6.log logs/6_err.log"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "touch logs/7.log logs/7_err.log"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo \"pvt_temp_all.sh | egrep 'min|max|average'\" > tsense.sh"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo \"pvt_temp_all.sh | egrep 'max'\" > max_tsense.sh"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'sz0=$(($1 * 5))' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'sz1=$(($1 / 1))' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'echo \"check available memory before starting ch0\"' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'grep MemAv /proc/meminfo' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'memtester -p 0x1080000000 $sz0\M $2 1> logs/01.log 2> logs/01_err.log &' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'echo \"check available memory after starting ch0\"' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'grep MemAv /proc/meminfo' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'memtester -p 0x2000000000 $sz1\M $2 1> logs/1.log 2> logs/1_err.log &' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'memtester -p 0x4000000000 $1\M $2 1> logs/2.log 2> logs/2_err.log &' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'memtester -p 0x5000000000 $1\M $2 1> logs/3.log 2> logs/3_err.log &' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'memtester -p 0x8000000000 $1\M $2 1> logs/4.log 2> logs/4_err.log &' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'memtester -p 0x9000000000 $1\M $2 1> logs/5.log 2> logs/5_err.log &' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'memtester -p 0xA000000000 $1\M $2 1> logs/6.log 2> logs/6_err.log &' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "echo -e 'memtester -p 0xB000000000 $1\M $2 1> logs/7.log 2> logs/7_err.log &' >> memtest"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)
    command = "chmod 777 *"
    hortaLinux.sendline(f"{command}")
    hortaLinux.expect('#', timeout=None)

def horta_linux(temp, mem, usbConLinux, oFile, horta, usbConMcu, copy):
    fd = serial.Serial(("/dev/tty" + usbConLinux), 115200, timeout=1) #Connect to the Serial port
    hortaLinux = fdpexpect.fdspawn(fd, encoding='utf-8') #Opens the serial port as a child process
    hortaLinux.delaybeforesend = 5 #Delays sending commands
    if hortaLinux.isalive():
        try:
            print(f'Connected to /dev/tty{usbConLinux}\n')
            if horta == "start":
                hortaLogin(hortaLinux)
            if copy == "copy":
                copyFiles(hortaLinux)
            if temp == 'check':
                tempCheck(hortaLinux, logfile)
            elif int(temp) > -100:
                thermalMachine(temp, hortaLinux)
                while True:
                    hortaLinux.sendline('./max_tsense.sh') #Make sure filename matches the one on your system
                    hortaLinux.expect('#', timeout=None)
                    chipTemp = str(hortaLinux.before) #Extracts the max temperature
                    if "random: crng init done" not in chipTemp:
                        chipTemp = chipTemp.replace("./max_tsense.sh", "")
                        chipTemp = chipTemp.replace("max temp: ", "")
                        chipTemp = chipTemp.replace("C", "")
                        chipTemp = chipTemp.replace(" ", "")
                        chipTemp = chipTemp.replace("\r\n", "")
                        print(f"Current Temperature is: {chipTemp}")
                        chipTemp = float(chipTemp)
                        if int(chipTemp) >= int(temp) - 30:
                            break
            if mem == "run-all":
                global margin1
                mcu = serial.Serial(f"/dev/tty{usbConMcu}", 57600, timeout=1) #Connect to the Serial port
                margin1 = "high"
                margin = margin1
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m, copy, margin, temp)
                margin1 = "nominal"
                margin = margin1
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m, copy, margin, temp)
                margin1 = "low"
                margin = margin1
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m, copy, margin, temp)
                hortaLinux.close()
            elif mem == 'run':
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m, copy, margin, temp)
                hortaLinux.close()
        except KeyboardInterrupt:
            print("\nInterrupted manually.\nNOTE: Test might have not finished yet and logfile might not have written some of the results")
            sys.exit(0)

def hortaLogin(hortaLinux):
    hortaLinux.sendline('root')
    hortaLinux.expect('Password: ', timeout=None) #Uncomment this and the next line if DUNE also requires password
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

def memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m, copy, margin, temp): #Function to start Memtester
    sleep(0.5)
    hortaLinux.sendline(f'./memtest {n} {m}') #Make sure filename matches the one on your system
    hortaLinux.expect('#', timeout=None)
    print(hortaLinux.before)
    i = 0
    w = 100
    sleep(3)
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
            sleep(2.5)
            status = mcu.read(mcu.inWaiting())
            status = str(status, 'utf-8')
            status = status.replace("\r\n","\n")
            print(status)
        hortaLinux.sendline('ps | grep memtest') #checks the running memtester processes
        hortaLinux.expect('#', timeout=None)
        hortaLinux.logfile_read = sys.stdout
        string2 = str(hortaLinux.before)
        if "panic" in string2.lower() or "kernel" in string2.lower() or "horta" in string2.lower() or "end" in string2.lower() or "trace" in string2.lower() or "cpu" in string2.lower() or "sdhci" in string2.lower():
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
            if copy == 'copy':
                copyFiles(hortaLinux)
            if margin1 == "high":
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                margin = "nominal"
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                margin = "low"
                marginSelect(mcu, margin, logfile)
                readHorta(mcu, logfile)
                memtest(hortaLinux, logfile, usbConMcu, usbConLinux, oFile, n, m)
                hortaLinux.close()
            elif margin1 == "nominal":
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
            cc = pexpect.spawn(f'python3 ThermalMachine3.py 10.1.0.3 -p off', encoding='utf-8')
            cc.expect(pexpect.EOF, timeout=None)
            cc.close()
            break
        else:
            warning(hortaLinux, mcu) #run warning script for safety
            thermalMachine(temp, hortaLinux)
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
def thermalMachine(temp, hortaLinux):
        hortaLinux.sendline('./max_tsense.sh') #Make sure filename matches the one on your system
        hortaLinux.expect('#', timeout=None)
        chipTemp = str(hortaLinux.before) #Extracts the max temperature
        if "random: crng init done" not in chipTemp:
            chipTemp = chipTemp.replace("./max_tsense.sh", "")
            chipTemp = chipTemp.replace("max temp: ", "")
            chipTemp = chipTemp.replace("C", "")
            chipTemp = chipTemp.replace(" ", "")
            chipTemp = chipTemp.replace("\r\n", "")
            chipTemp = float(chipTemp)
        if int(temp) >= 120:
            lowRange = 120
            highRange = 120
            machineTemp = int(temp)
            if int(chipTemp) < int(temp) - 40:
                machineTemp = 150
            else:
                machineTemp = int(temp) - 35
            if int(chipTemp) < lowRange:
                machineTemp = machineTemp + 2
                if machineTemp > 150:
                    machineTemp = 150
            elif int(chipTemp) > highRange:
                machineTemp = 75
            cc = pexpect.spawn(f'python3 ThermalMachine3.py 10.1.0.3 -p on -t {machineTemp}', encoding='utf-8')
            cc.expect(pexpect.EOF, timeout=None)
            cc.close()
        

def warning(hortaLinux, mcu):
    hortaLinux.sendline('./max_tsense.sh') #Make sure filename matches the one on your system
    hortaLinux.expect('#', timeout=None)
    string = str(hortaLinux.before) #Extracts the max temperature
    if "random: crng init done" not in string:
        string = string.replace("./max_tsense.sh", "")
        string = string.replace("max temp: ", "")
        string = string.replace("C", "")
        if float(string) > 125 and float(string) < 140: #If the temperature is in range of danger, prints a warning
            print("Warning temperature is getting too high!!!")
        elif float(string) >= 140: #If temperature is higher than damage range, powers down the board
            hortaLinux.close()
            print("Temperature is too high! Shutting down Horta!")
            powDir(mcu)
            mcu.write(b"force\r") #Change to force
            sleep(0.5)
            mcu.write(b"fl_newpw\r") #Forceswitches horta board off
            logfile.write('Power force-switched off\n')
            print('Power force-switched off\n') #Prints to show power switched off
            sleep(3)
            sys.exit()

argParser() #Calling the Argument Passer function to start executing
sys.exit(0)
