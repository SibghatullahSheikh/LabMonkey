from serial import Serial
from sys import stdout
from time import time, sleep


class RS232Transport:
    """
    RS232 Faulhaber Motion Control
    """
    def __init__(self, port, baud=9600, verbose=False, log_stream=stdout):
        self.s = Serial(port, baud, timeout=1)
        self.verbose = verbose
        self.log_stream = log_stream
    
    def log(self, msg):
        if self.verbose:
            self.log_stream.write(msg)
    
    def command(self, c):
        self.log("> %s" % c)
        self.s.write(c)
        response = self.s.readline().rstrip()
        self.log(": %s\n" % response)
        return response


class Motor:
    def __init__(self, transport, node=None):
        self.transport = transport
        
        if node is None:
            self.cmd_format = "%s\n"
        else:
            self.cmd_format = "%d%%s\n" % node
        
        self.enable()
    
    def command(self, c):
        self.transport.command(self.cmd_format % c)
    
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
    
    def get_position(self):
        return int(self.command('POS'))
    
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
    
    ###########################################################################
    # Record / Play
    ###########################################################################
    def record(self, seconds, min_dt=0.01):
        self.disable() # Do not drive
        
        t0, t2, p = time(), 0, self.get_position()
        positions = [(t2, p)]
        t1 = t2
        
        while t2 < seconds:
            t2 = (time() - t0)
            positions.append((t2, self.get_position()))
            
            dt = (t2 - t1)
            if dt < min_dt:
                sleep(min_dt - dt)
            t1 = t2
        
        self.enable() # Restore drive
        return positions
    
    def play(self, positions, min_dp=9):
        t0, p0 = time(), self.get_position()
        
        for t1, p1 in positions:
            if abs(p1 - p0) > min_dp:
                self.move_to_location(p1)
                p0 = p1
            
            dt = (t0 + t1) - time()
            if dt > 0:
                sleep(dt)


if __name__ == '__main__':
    transport = RS232Transport('/dev/ttyUSB0')
    
    motors = [Motor(transport, i) for i in [0, 1, 3]]
    
    for i in range(3):
        for m in motors:
            m.velocity(1000)
        sleep(3)
        
        for m in motors:
            m.stop()
        sleep(3)
    
    """
    m.home()
    
    print "Recording motion:"
    positions = m.record(4)
    
    print "Play motion:"
    for i in range(3):
        print "Iteration:", (i+1)
        m.play(positions)
    """