from serial import Serial
from sys import stdout
from time import time, sleep
import json

from configuration import LABMONKEY


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
        return self.transport.command(self.cmd_format % c)
    
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


class LabMonkey:
    def __init__(self):
        transport = RS232Transport(LABMONKEY['com'], verbose=LABMONKEY['debug'])
        
        self.motors = []
        for m_data in LABMONKEY['motors']:
            m = Motor(transport, m_data['id'])
            
            m.set_max_speed(m_data['rpm'])
            m.set_max_acceleration(m_data['acc'])
            m.set_max_deceleration(m_data['acc'])
            
            m.disable()
            
            self.motors.append(m)
        
        self.waypoints = []
    
    def set_home(self):
        for m in self.motors:
            m.home()
    
    def enable_motors(self):
        for m in self.motors:
            m.enable()
    
    def disable_motors(self):
        for m in self.motors:
            m.disable()
    
    def play_waypoints(self, waypoints, delay=1):
        for w in waypoints:
            for m, p in zip(self.motors, w):
                m.move_to_location(p)
            sleep(delay)
    
    def parse_int(self, s, default=1):
        i = default
        try:
            i = int(s)
        except Exception, e:
            pass
        return i
    
    def run(self):
        while True:
            cmd = raw_input("> ")
            if cmd == 'r':
                self.waypoints.append([m.get_position() for m in self.motors])
            
            elif cmd.startswith('play'):
                iterations = self.parse_int(cmd[4:])
                self.enable_motors()
                for i in range(iterations):
                    self.play_waypoints(self.waypoints)
                self.disable_motors()
            
            elif cmd.startswith('cycle'):
                iterations = self.parse_int(cmd[5:])
                rev_waypoints = list(reversed(self.waypoints))
                
                self.enable_motors()
                for i in range(iterations):
                    self.play_waypoints(self.waypoints)
                    self.play_waypoints(rev_waypoints)
                self.disable_motors()
                
            elif cmd == 'show':
                print self.waypoints
            
            elif cmd.startswith('save'):
                try:
                    filename = cmd[5:]
                    with open(filename, 'w') as f:
                        f.write(json.dumps(self.waypoints, indent=4, separators=(',', ': ')))
                        print 'Saved waypoints on: %s' % filename
                except Exception, e:
                    print e
            
            elif cmd.startswith('load'):
                try:
                    filename = cmd[5:]
                    with open(filename, 'r') as f:
                        self.waypoints = json.loads(f.read())
                        print 'Loaded waypoints from: %s' % filename
                except Exception, e:
                    print e
            
            elif cmd == 'reset':
                self.waypoints = []
            
            elif cmd == 'home':
                self.set_home()
            
            elif cmd.startswith('exit'):
                break


if __name__ == '__main__':
    LabMonkey().run()
