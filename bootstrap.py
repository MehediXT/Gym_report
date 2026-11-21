"""
Bootstrap environment loader for the Gym Management Application.
Ensures required Tkinter and C libraries are dynamically loaded if running in an isolated or user-space environment.
"""

import os
import sys
import ctypes

def setup_environment():
    user_local = os.path.expanduser('~/.local')
    
    # 1. Preload Tkinter shared libraries if present in ~/.local
    tk_so = os.path.join(user_local, 'usr/lib/x86_64-linux-gnu/libtk8.6.so')
    blt_so = os.path.join(user_local, 'usr/lib/libBLT.2.5.so.8.6')
    
    if os.path.exists(tk_so):
        try:
            ctypes.CDLL(tk_so)
        except Exception:
            pass
            
    if os.path.exists(blt_so):
        try:
            ctypes.CDLL(blt_so)
        except Exception:
            pass

    # 2. Add local python library paths to sys.path
    py312_path = os.path.join(user_local, 'usr/lib/python3.12')
    dynload_path = os.path.join(user_local, 'usr/lib/python3.12/lib-dynload')
    dist_path = os.path.join(user_local, 'usr/lib/python3/dist-packages')
    
    for p in [py312_path, dynload_path, dist_path]:
        if os.path.exists(p) and p not in sys.path:
            sys.path.insert(0, p)

    # 3. Configure Tk & Tcl library paths
    tk_lib = os.path.join(user_local, 'usr/share/tcltk/tk8.6')
    if os.path.exists(tk_lib) and 'TK_LIBRARY' not in os.environ:
        os.environ['TK_LIBRARY'] = tk_lib
        
    tcl_lib = '/usr/share/tcltk/tcl8.6'
    if os.path.exists(tcl_lib) and 'TCL_LIBRARY' not in os.environ:
        os.environ['TCL_LIBRARY'] = tcl_lib
        
    # Also ensure current directory is in sys.path
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    if curr_dir not in sys.path:
        sys.path.insert(0, curr_dir)

setup_environment()
