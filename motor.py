from serial import Serial
from sys import stdout


class Motor:
    """
    RS232 Faulhaber Motion Control
    """
    def __init__(self, port, baud=9600, node=None, verbose=False, log_stream=stdout):
        self.s = Serial(port, baud, timeout=1)
        self.set_node(node)
        self.verbose = verbose
        self.log_stream = log_stream
        self.enable()
    
    def log(self, msg):
        if self.verbose:
            self.log_stream.write(msg)
    
    ###########################################################################
    # Protocol
    ###########################################################################
    def set_node(self, node):
        if node is None:
            self.cmd_format = "%s\n"
        else:
            self.cmd_format = "%d%%s\n" % node
    
    def command(self, command):
        self.log("> %s" % command)
        self.s.write(self.cmd_format % command)
        response = self.s.readline().rstrip()
        self.log(": %s\n" % response)
        return response
    
    ###########################################################################
    # Enable / Disable
    ###########################################################################
    def enable(self):
        return self.command('EN')
    
    def disable(self):
        return self.command('DI')
    
    def __del__(self):
        self.disable()
    
    ###########################################################################
    # Velocity Control
    ###########################################################################
    def velocity(self, rpm):
        return self.command('V%d' % rpm)
    
    def stop(self):
        self.velocity(0)
    
    def set_max_speed(self, rpm):
        self.command("SP%d" % rpm)
    
    def set_max_acceleration(self, acc):
        self.command("AC%d" % acc)
    
    def set_max_deceleration(self, dec):
        self.command("DEC%d" % dec)
    
    ###########################################################################
    # Position Control
    ###########################################################################
    def move(self):
        self.command('M')
    
    def load_relative(self, steps):
        self.command('LR%d' % steps)
    
    def move_steps(self, steps):
        self.load_relative(steps)
        self.move()
    
    def home(self, position=None):
        cmd = "HO" # Set current position as 0
        if position is not None:
            # Set specified position as 0
            cmd += "%d" % position
        self.command(cmd)
    
    def load_absolute(self, position):
        self.command('LA%d' % position)
    
    def move_to_location(self, location):
        self.load_absolute(location)
        self.move()
    
    ###########################################################################
    # Sequence Programs
    ###########################################################################
    def start_prog(self):
        self.command("PROGSEQ")
    
    def end_prog(self):
        self.command("END")
    
    def delay(self, seconds):
        self.command("DELAY%d" % int(seconds*100))
    
    def run_prog(self):
        self.command("ENPROG ")


if __name__ == '__main__':
    from time import sleep
    m = Motor('/dev/ttyUSB0', verbose=True)
    m.home()
    
    m.start_prog()
    m.move_to_location(1000)
    m.delay(1)
    m.move_to_location(0)
    m.end_prog()
    
    for i in range(4):
        m.run_prog()
        sleep(2)
