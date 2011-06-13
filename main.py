import sys
import httplib
import socket

if sys.platform != 'darwin':
    import appuifw
    import e32
    import key_codes

HOST = "192.168.1.108"
PORT = 8080

""" Iphone remote used codes
north        "GET /xbmcCmds/xbmcHttp?command=SendKey(270) HTTP/1.1" 404 2360
south        "GET /xbmcCmds/xbmcHttp?command=SendKey(271) HTTP/1.1" 404 2360
west         "GET /xbmcCmds/xbmcHttp?command=SendKey(272) HTTP/1.1" 404 2360
est          "GET /xbmcCmds/xbmcHttp?command=SendKey(273) HTTP/1.1" 404 2360
center       "GET /xbmcCmds/xbmcHttp?command=SendKey(256) HTTP/1.1" 404 2360
long center  "GET /xbmcCmds/xbmcHttp?command=Stop() HTTP/1.1" 404 2354
back         "GET /xbmcCmds/xbmcHttp?command=Action(9) HTTP/1.1" 404 2357
back long    "GET /xbmcCmds/xbmcHttp?command=Action(10) HTTP/1.1" 404 2358
current      "GET /xbmcCmds/xbmcHttp?command=SendKey(0xF143) HTTP/1.1" 404 2363
view         "GET /xbmcCmds/xbmcHttp?command=Action(18) HTTP/1.1" 404 2358
view long    "GET /xbmcCmds/xbmcHttp?command=Action(199) HTTP/1.1" 404 2359
set volume   "GET /xbmcCmds/xbmcHttp?command=setvolume(100.000000) HTTP/1.1" 404 2369
get volume   "GET /xbmcCmds/xbmcHttp?command=GetVolume HTTP/1.1" 404 2357

status command:
"GET /xbmcCmds/xbmcHttp?command=getcurrentplaylist HTTP/1.1" 404 2366
"""

class ActionsList:
    # http://trac.xbmc.org/browser/branches/linuxport/XBMC/guilib/Key.h?rev=16176
    ACTION_MOVE_LEFT      = 1
    ACTION_MOVE_RIGHT     = 2
    ACTION_MOVE_UP        = 3
    ACTION_MOVE_DOWN      = 4
    ACTION_PAGE_UP        = 5
    ACTION_PAGE_DOWN      = 6
    ACTION_SELECT_ITEM    = 7    
    ACTION_HIGHLIGHT_ITEM = 8
    ACTION_PARENT_DIR     = 9
    ACTION_PREVIOUS_MENU  = 10
    ACTION_SHOW_INFO      = 11
    ACTION_STOP           = 13
    ACTION_MOUSE          = 90
    ACTION_BACKSPACE      = 110
    ACTION_ENTER          = 135


actions = ActionsList()

class Settings(object):

    filename = "xbmc-settings"
    
    def __init__(self):
        import e32dbm
        try:
            # Try to open an existing file
            self.data = e32dbm.open(self.filename,"wf")
        except:
            # Failed: Assume the file needs to be created
            self.data = e32dbm.open(self.filename,"nf")
        
        self.draw()
    
    def _get_host(self):
        return self.getValue('HOST')
    host = property(_get_host)

    def _get_port(self):
        return self.getValue('PORT')
    port = property(_get_port)
            
    def _setValue(self,key,value):
        if str(value) == value:
            # if value is a string, it needs special treatment
            self.config[key] = "u\"%s\"" % value
        else:
            # otherwise simply convert it to a string
            self.config[key] = str(value)

    def _getValue(self,key):
        try:
            return eval(self.config[key])
        except:
            # Assume item doesn't exist (yet), so return None
            return None

    def close(self):
        self.data.close()
    
    def draw(self):

        data = [
            (u'Host','text', self.host or u'192.168.0.100'),
            (u'Port','number', self.port or 8080)
        ]
        flags = appuifw.FFormEditModeOnly
        form = appuifw.Form(data, flags)
        form.execute()

class Remote(object):
    _command_url = '/xbmcCmds/xbmcHttp?command='

    def __init__(self, connection):
        self.connection = connection
        self.connected  = False
        self.webServerStatus()
        print 'connected'
    
    def webServerStatus(self):
        self.connection.request("GET", self._command_url + "getcurrentplaylist()")
        response = self.connection.getresponse()
    
    def fireAction(self, action_code):
        return self.fireCommand("Action(%d)" % action_code)
    
    def fireCommand(self, command):
        try:
            self.connection.request("GET", self._command_url + command )
            response = self.connection.getresponse()
            self.connected = True
            if response.status!=200:
                raise Exception("invalid action id %d : reponse %s" % (action_code, response.code))
            return response.read()
        except Exception, e:
            print e
            self.connected = False        
        
    def up(self):
        self.fireAction(actions.ACTION_MOVE_UP)
    def down(self):
        self.fireAction(actions.ACTION_MOVE_DOWN)
    def left(self):
        self.fireAction(actions.ACTION_MOVE_LEFT)
    def right(self):
        self.fireAction(actions.ACTION_MOVE_RIGHT)
    def select(self):
        self.fireAction(actions.ACTION_SELECT_ITEM)
    
    def stop(self):
        self.fireCommand('Stop')
    def back(self):
        self.fireAction(actions.ACTION_PARENT_DIR)
    def prevMenu(self):
        self.fireAction(actions.ACTION_PREVIOUS_MENU)


connection = httplib.HTTPConnection(HOST, PORT)
remote = Remote(connection)

def sel_access_point():
    """ Select and set the default access point.
        Return the access point object if the selection was done or None if not
    """
    from appuifw import popup_menu
    aps = socket.access_points()
    if not aps:
        note(u"No access points available","error")
        return None

    ap_labels = map(lambda x: x['name'], aps)
    item = popup_menu(ap_labels,u"Access points:")
    if item is None:
        return None

    apo = socket.access_point(aps[item]['iapid'])
    socket.set_default_access_point(apo)

    return apo

def symbian_interface():
    
    class Keyboard(object):
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

    keyboard = Keyboard()
    
    def quit():
        global running
        running=0
        appuifw.app.set_exit()
    
    running = 1
    
    appuifw.app.screen='normal'
    
    canvas=appuifw.Canvas(event_callback=keyboard.handle_event, redraw_callback=None)
    appuifw.app.body=canvas
    
    appuifw.app.exit_key_handler=quit
    
    appuifw.app.menu = [
        (u'Preferences', Settings), 
    ]
        
    while running:

        if keyboard.pressed(key_codes.EScancodeLeftArrow):
            remote.left()
        elif keyboard.pressed(key_codes.EScancodeRightArrow):
            remote.right()
        elif keyboard.pressed(key_codes.EScancodeDownArrow):
            remote.down()
        elif keyboard.pressed(key_codes.EScancodeUpArrow):
            remote.up()
        elif keyboard.pressed(key_codes.EScancodeSelect):
            remote.select()
        elif keyboard.pressed(key_codes.EStdKeyBackspace):
            remote.back()
        elif keyboard.pressed(key_codes.EKey1):
            remote.prevMenu()
        elif keyboard.pressed(key_codes.EStdKeyIncVolume):
            remote.increase_volume()
        elif keyboard.pressed(key_codes.EStdKeyDecVolume):
            remote.decrease_volume()
        
        elif keyboard.pressed(key_codes.EKey0):
            running = False        
        
        if not remote.connected:
            running = False
            print "connection closed"
        
        e32.ao_yield()    
    
if __name__ == '__main__':
    if sys.platform != 'darwin':
        symbian_interface()
    else:
        from develop import terminal_interface
        terminal_interface()
