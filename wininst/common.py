import _winreg

def refreshEnvironment():
    HWND_BROADCAST      = 0xFFFF
    WM_SETTINGCHANGE    = 0x001A
    SMTO_ABORTIFHUNG    = 0x0002
    sParam              = "Environment"

    import win32gui
    res1, res2          = win32gui.SendMessageTimeout(HWND_BROADCAST,
                            WM_SETTINGCHANGE, 0, sParam, SMTO_ABORTIFHUNG, 100)
        
def append_to_reg_path( new_dir ) :
    """
    appends a new dir to the registry PATH value
    """
    reg = _winreg.ConnectRegistry( None, _winreg.HKEY_LOCAL_MACHINE )
    #
    # open key for reading, to save and print out old value
    #
    key = _winreg.OpenKey(
        reg,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment" )
    
    old_path = _winreg.QueryValueEx( key, "path" )[0]

    _winreg.CloseKey( key )

    #
    # reopen key for writing new value
    #
    key = _winreg.OpenKey(
        reg,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        0,
        _winreg.KEY_ALL_ACCESS )

    new_path = "%s;%s" % (old_path, new_dir)

    #
    # append new_dir to the PATH
    #
    _winreg.SetValueEx( key, "path", 0, _winreg.REG_EXPAND_SZ, new_path )

    _winreg.CloseKey( key )
    _winreg.CloseKey( reg )
    
    try:
        refreshEnvironment()
    except:
        print
        print "WARNING: The registry has been modified."
        print "You may need to restart your Windows session in order for the"
        print "changes to be seen by the application."
        print

def append_to_reg_pathext():
    """
    appends .py and .pyc to the registry PATHEXT value
    """
    reg = _winreg.ConnectRegistry( None, _winreg.HKEY_LOCAL_MACHINE )
    #
    # open key for reading, to save and print out old value
    #
    key = _winreg.OpenKey(
        reg,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment" )
    
    old_pathext = _winreg.QueryValueEx( key, "PATHEXT" )[0]
    _winreg.CloseKey( key )
    
    #
    # reopen key for writing new value
    #
    key = _winreg.OpenKey(
        reg,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        0,
        _winreg.KEY_ALL_ACCESS )
    
    new_pathext = old_pathext + ";.PY;.PYC"
    
    _winreg.SetValueEx( key, "PATHEXT", 0, _winreg.REG_SZ, new_pathext )

    _winreg.CloseKey( key )
    _winreg.CloseKey( reg )


def register_association_with_shell(desc, cmd):
    """
    Adds command to shell association for .py files, enabling
    right clicking to edit the file
    """
    reg = _winreg.ConnectRegistry( None, _winreg.HKEY_LOCAL_MACHINE )
    #
    # open key for writing
    #
    key = _winreg.OpenKey(
        reg,
        r"SOFTWARE\Classes\Python.File\shell",
        0,
        _winreg.KEY_ALL_ACCESS )
        
    new_key = _winreg.CreateKey(key, desc)
    _winreg.SetValue(new_key, "command", _winreg.REG_SZ, cmd)

    _winreg.CloseKey( new_key )
    _winreg.CloseKey( key )
    _winreg.CloseKey( reg )
    
def add_shortcut(target,description,link_file,*args,**kw):
    """
    example: add_shortcut("python.exe", "example script", "example.lnk",
                          "example.py", "", "path_to_icon.ico")
    """
    if not os.path.isfile(link_file):
        #this should call the function in wininst module, if its
        # not imported in enstaller_app, this will fail
        try:
            create_shortcut(target, description, link_file,*args,**kw)
            file_created(link_file)
        except:
            print "shortcut not created, wininst module probably missing"
                                
