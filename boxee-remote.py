import re
import sys
import httplib
import socket
import time
import thread

if sys.platform == 'symbian_s60':
    import appuifw
    from graphics import Image
    
HOST = "192.168.10.99"
PORT = 8080
# timeout to disconnect
INACTIVITY_TIMEOUT = 10

class BoxeeRemote(object):
    
    _command_url = '/xbmcCmds/xbmcHttp?command='

    def __init__(self, host, port):
        self._host = host
        self._port = port
        self.connection = None
        self.connected  = False
        self.disconnect_timeout = time.time()
        # self.disconnect_thread = thread.start_new_thread(self._looping_thread, tuple())
        self.webServerStatus()
        print 'connected'
    
    def _looping_thread(self):
        import time
        while 1:
            time.sleep(5)
            timeout = time.time() - self.disconnect_timeout > INACTIVITY_TIMEOUT
            if self.connection and timeout:
                self.connection.close()
                appuifw.query(u"CONNECTION CLOSED!!","query")
                self.connection = None
    
    def _get_sure_you_connect(self):
        if self.connection:
            self.disconnect_timeout = time.time()
        else:
            # in case there is no connection i have to create a new one
            self.connection = httplib.HTTPConnection(self._host, self._port)
    
    def webServerStatus(self):
        self.fireCommand('GetVolume')
    
    def fireAction(self, action_code):
        self._get_sure_you_connect()
        return self.fireCommand("Action(%d)" % action_code)
    
    def fireCommand(self, command):
        self._get_sure_you_connect()
        try:
            self.connection.request("GET", self._command_url + command )
            response = self.connection.getresponse()
            self.connected = True
            if response.status != 200:
                raise Exception("invalid action id %s : reponse %s" % (command, response.msg))
            return response.read()
        except Exception, e:
            print e
            self.connected = False        

    def up(self):
        self.fireCommand('SendKey(270)')
    def down(self):
        self.fireCommand('SendKey(271)')
    def left(self):
        self.fireCommand('SendKey(272)')
    def right(self):
        self.fireCommand('SendKey(273)')
    
    def select(self):
        self.fireCommand('SendKey(256)')
    def stop(self):
        self.fireCommand('Stop')
    def back(self):
        self.fireCommand('SendKey(275)')
    
    def getVolume(self):
        response = self.fireCommand('getVolume')
        response = re.sub("</{0,1}[a-z]+/{0,1}>", '', response)
        volume = float(response)
        return volume
    def volumeUp(self):
        current_volume = self.getVolume()
        self.fireCommand('setVolume(%d)' % (current_volume + 10))
    def volumeDown(self):
        current_volume = self.getVolume()
        self.fireCommand('setVolume(%d)' % (current_volume - 10))
    def volumeMute(self):
        self.fireCommand("Mute()")
    
    def isKeybordActive(self):
        response = self.fireCommand('getKeyboardText')
        return 'active="1"' in response
    
    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
        

class SymbianKeyboard(object):
    
    def __init__(self,onevent=lambda:None):
        self._keyboard_state={}
        self._downs={}
        self._onevent=onevent
    
    def handle_event(self,event):
        if event['type'] == appuifw.EEventKeyDown:
            code=event['scancode']
            if not self.is_down(code):
                self._downs[code]=self._downs.get(code,0)+1
            self._keyboard_state[code]=1
        elif event['type'] == appuifw.EEventKeyUp:
            self._keyboard_state[event['scancode']]=0
        self._onevent()
    
    def is_down(self,scancode):
        return self._keyboard_state.get(scancode,0)
    
    def pressed(self,scancode):
        if self._downs.get(scancode,0):
            self._downs[scancode]-=1
            return True
        return False

class BoxeeApplication(object):
    
    def __init__(self):
        self.keyboard = SymbianKeyboard()
        self.appuifw = appuifw
        self.app = appuifw.app
        self.app.title = u"Boxee Remote"
        # self.app.screen = 'large'
        self.body = appuifw.Canvas(event_callback=self.keyboard.handle_event, 
                                   redraw_callback=None)
        self.app.body = self.body
        self.app.exit_key_handler = self.quit
        self.running = True
        self.get_accesspoint()
        host, port = self.get_host()
        self.remote = BoxeeRemote(host, port)
        self.body.blit(Image.open('e:\\Python\\gui_background.jpg'))
        self.menu()
    
    def get_config(self):
        try:
            f=open('c:\\data\\boxee-remote.conf','rb')
            config = eval(f.read())
            f.close()
        except:
            return {}
        return config

    def save_config(self, config):
        f = open('c:\\data\\boxee-remote.conf','w')
        f.write(repr(config))
        f.close()
    
    def clear_preferences(self):
        self.save_config({})
    
    def get_host(self):
        config = self.get_config()
        if not config.get('host'):
            config['host'] = appuifw.query(u"Host name or IP","text")
            self.save_config(config)
        if not config.get('port'):
            config['port'] = appuifw.query(u"Host port","number")
            self.save_config(config)
        return config.get('host'), config.get('port')
    
    def get_accesspoint(self):
        config = self.get_config()
        if not config.get('apid') == None :
            apid = config.get('apid')
            apo = socket.access_point(apid)
            socket.set_default_access_point(apo)
        else:
            self.set_accesspoint()

    def set_accesspoint(self):
        apid = socket.select_access_point()
        if appuifw.query(u"Set as default access point","query") == True:
            appuifw.note(u"Saved default access point ", "info")
            config = self.get_config()
            config['apid'] = apid
            self.save_config(config)
            apo = socket.access_point(apid)
            socket.set_default_access_point(apo)

    def menu(self):
        self.app.menu = [
            (u'Preferences', self.preferences),
            (u'Clear preferences', self.clear_preferences),
            (u'About', self.about),
            (u'Exit', self.quit),
        ]
    
    def preferences(self):
        pass
    
    def about(self):
        pass
    
    def quit(self):
        if self.remote:
            self.remote.close()
            
        self.running = False
    
    def loop(self):
        import key_codes
        import e32
        start_time = time.time()
        
        while self.running:
            if self.keyboard.pressed(key_codes.EScancodeLeftArrow):
                self.remote.left()
            elif self.keyboard.pressed(key_codes.EScancodeRightArrow):
                self.remote.right()
            elif self.keyboard.pressed(key_codes.EScancodeDownArrow):
                self.remote.down()
            elif self.keyboard.pressed(key_codes.EScancodeUpArrow):
                self.remote.up()
            elif self.keyboard.pressed(key_codes.EScancodeSelect):
                self.remote.select()
            elif self.keyboard.pressed(key_codes.EStdKeyBackspace):
                self.remote.back()
                
            elif self.keyboard.pressed(key_codes.EKey7):
                self.remote.volumeDown()
            elif self.keyboard.pressed(key_codes.EKey8):
                self.remote.volumeMute()
            elif self.keyboard.pressed(key_codes.EKey9):
                self.remote.volumeUp()                
            
            elif self.keyboard.pressed(key_codes.EKey0):
                self.quit()
            
            if not self.remote.connected:
                self.quit()
                print "connection closed"
            
            e32.ao_yield()
        
        if not start_time + 2000 < time.time():
            if appuifw.query(u"Do you want to reset the preferences?","query") == True:
                self.clear_preferences()
        
        self.quit()
        
if __name__ == '__main__':
    
    if sys.platform == 'symbian_s60':
        app = BoxeeApplication()
        app.loop()
    else:
        remote = BoxeeRemote(HOST, PORT)
        remote.webServerStatus()
        time.sleep(10)
        remote.webServerStatus()
        