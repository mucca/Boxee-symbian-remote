def terminal_interface():
    import Tkinter as tk

    def keypress(event):
        if event.keysym == 'Escape':
            root.destroy()
        x = event.char
        
        if x == "w":
            remote.up()
        elif x == "a":
            remote.left()
        elif x == "s":
            remote.down()
        elif x == "d":
            remote.right()
        elif x == 'q':
            remote.stop()
        elif x == "1":
            remote.select()
        elif x == "2":
            remote.back()
        elif x == '3':
            remote.prevMenu()
        else:
            print 'not found' , x
    
    root = tk.Tk()
    root.bind_all('<Key>', keypress)
    root.mainloop()
