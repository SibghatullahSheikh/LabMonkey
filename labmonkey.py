from serial import Serial
from sys import stdout
from time import sleep
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
    POSITION_ATTAINED = 0x10000
    
    def __init__(self, transport, node=None):
        self.transport = transport
        
        if node is None:
            self.cmd_format = "%s\n"
        else:
            self.cmd_format = "%d%%s\n" % node
        
        self.enable()
    
    def set_max_vel(self, v):
        self.max_vel = v
    
    def command(self, c):
        return self.transport.command(self.cmd_format % c)
    
    ###########################################################################
    # Enable / Disable / Status
    ###########################################################################
    def enable(self):
        return self.command('EN')
    
    def disable(self):
        return self.command('DI')
    
    def __del__(self):
        self.disable()
    
    def operation_status(self):
        return int(self.command('OST'))
    
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
    
    def set_acceleration(self, acc):
        self.acceleration = acc
        self.set_max_acceleration(acc)
        self.set_max_deceleration(acc)
    
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
        self.last_position = position
    
    def move_to_location(self, location):
        self.load_absolute(location)
        self.move()
    
    def get_position(self):
        self.last_position = int(self.command('POS'))
        return self.last_position
    
    def wait_position(self):
        while (self.operation_status() & Motor.POSITION_ATTAINED) == 0:
            sleep(0.1)
    
    ###########################################################################
    # Sequence Programs
    ###########################################################################
    def start_prog(self):
        self.command("PROGSEQ")
    
    def end_prog(self):
        self.command("END")
    
    def delay(self, seconds):
        self.command("DELAY%d" % int(seconds*1000))
    
    def run_prog(self):
        self.command("ENPROG ")


class LabMonkey:
    def __init__(self):
        transport = RS232Transport(LABMONKEY['com'], verbose=LABMONKEY['debug'])
        
        self.motors = []
        for m_data in LABMONKEY['motors']:
            m = Motor(transport, m_data['id'])
            m.set_max_vel(m_data['max_vel'])
            m.set_acceleration(m_data['acc'])
            m.disable()
            self.motors.append(m)
    
    def set_home(self):
        for m in self.motors:
            m.home()
    
    def enable_motors(self):
        for m in self.motors:
            m.enable()
    
    def disable_motors(self):
        for m in self.motors:
            m.disable()
    
    def wait_position(self):
        for m in self.motors:
            m.wait_position()
    
    def get_positions(self):
        return [m.get_position() for m in self.motors]
    
    def play_waypoints(self, waypoints, wait_completion=True):
        self.get_positions() # update motor positions
        
        for w in waypoints:
            # Tweak motor velocities to finish motion at the same time
            movement_time = 0
            distances = []
            for m, p in zip(self.motors, w):
                d = abs(m.last_position - p)
                distances.append(d)
                movement_time = max(movement_time, (d / m.max_vel))
            
            for m, d in zip(self.motors, distances):
                v = max((d / movement_time), 60)
                m.set_max_speed(v)
            
            for m, p in zip(self.motors, w):
                m.move_to_location(p)
            
            if wait_completion:
                self.wait_position()
    
    def parse_int(self, s, default=1):
        i = default
        try:
            i = int(s)
        except Exception, e:
            pass
        return i
    
    def run(self):
        waypoints = []
        
        while True:
            cmd = raw_input("> ").split()
            if cmd[0] == 'r':
                waypoints.append(self.get_positions())
            
            elif cmd[0] == 'play':
                iterations = self.parse_int(cmd[1])
                self.enable_motors()
                for i in range(iterations):
                    self.play_waypoints(waypoints)
                self.disable_motors()
            
            elif cmd[0] == 'cycle':
                iterations = self.parse_int(cmd[1])
                rev_waypoints = list(reversed(waypoints))
                
                self.enable_motors()
                for i in range(iterations):
                    self.play_waypoints(waypoints)
                    self.play_waypoints(rev_waypoints)
                self.disable_motors()
            
            elif cmd[0] == 'show':
                print waypoints
            
            elif cmd[0] == 'save':
                try:
                    with open(cmd[1], 'w') as f:
                        f.write(json.dumps(waypoints, indent=4, separators=(',', ': ')))
                        print 'Saved waypoints on: %s' % cmd[1]
                except Exception, e:
                    print e
            
            elif cmd[0] == 'load':
                try:
                    with open(cmd[1], 'r') as f:
                        waypoints = json.loads(f.read())
                        print 'Loaded waypoints from: %s' % cmd[1]
                except Exception, e:
                    print e
            
            elif cmd[0] == 'clear':
                waypoints = []
            
            elif cmd[0] == 'home':
                self.set_home()
            
            elif cmd[0] == 'exit':
                break


if __name__ == '__main__':
    LabMonkey().run()
