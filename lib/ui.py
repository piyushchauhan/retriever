"""Database Toolkit UI

This module contains the UI elements of the database toolkit platform. 

This module should not be run directly; instead, individual scripts, when run,
should run the launch_wizard function.

"""

import sys
import wx
import wx.wizard
from tools import final_cleanup
from dbtk.lib.ui_pages import DbTkWizard
from dbtk.lib.engines import ALL_ENGINES


def launch_wizard(lists):    
    """Launches the download wizard."""
    print "Launching Database Toolkit wizard . . ."                    
    
    # Create the wxPython app and wizard 
    app = wx.PySimpleApp(False)    
    wizard = DbTkWizard(None, -1, "Database Toolkit Wizard", 
                        lists, ALL_ENGINES)

    # Run the wizard and, if successful, download datasets
    if wizard.RunWizard(wizard.TITLE):
        # Get a list of scripts to be downloaded
        scripts = []
        checked_scripts = wizard.DATASET.scriptlist.GetCheckedStrings()
        for script in wizard.dbtk_list:
            dl = False
            if len(wizard.dbtk_list) > 1:
                if script.name in checked_scripts:
                    dl = True
            else:
                dl = True
            if dl:
                scripts.append(script)
                
        # Find the script with the longest name to set size of progress dialog        
        longestname = 20
        for script in scripts:
            if len(script.name) > longestname:
                longestname = len(script.name)
        
        # Create a frame to contain the progress dialog
        class Frame(wx.Frame):
            def __init__(self):
                wx.Frame.__init__(self, None, title="")
                self.progressMax = 100
                self.count = 0
                self.timer = wx.Timer(self)
                self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
                self.timer.Start(1)
                
            def OnTimer(self, evt):
                self.timer.Stop()
                # Create progress dialog 
                self.dialog = wx.ProgressDialog("Download Progress", 
                                           "Downloading datasets . . ." + 
                                           " " * longestname + "\n", 
                                           maximum = len(scripts) + 1, 
                                           style=wx.PD_CAN_ABORT | 
                                                 #wx.PD_CAN_SKIP |
                                                 wx.PD_ELAPSED_TIME |
                                                 wx.PD_APP_MODAL
                                            )
                
                self.dialog.Show()
                
                scriptnum = 0
        
                # Allow exception handling for "skip" and "cancel" buttons
                class UserSkipped(Exception):
                    pass
                class UserAborted(Exception):
                    pass
                
                # On stdout, the progress dialog updates
                class update_dialog:
                    """This function is called whenever the print statement is used,
                    and redirects the output to the progress dialog."""
                    def __init__(self, frame):
                        self.frame = frame
                    def write(self, s):                
                        txt = s.strip().replace("\b", "")
                        if txt:
                            prog = scriptnum
                            if prog < 1:
                                prog = 1
                            (keepgoing, skip) = self.frame.dialog.Update(prog,
                                                              msg + "\n" + txt)
                            if not keepgoing:
                                raise UserAborted
                            #if skip:
                            #    wx.MessageBox("SKIP")
                            #    raise UserSkipped
                
                self.dialog.Pulse("Connecting to database:")
                        
                # Get options from wizard
                engine = wizard.CONNECTION.engine
                options = wizard.CONNECTION.option
                engine.keep_raw_data = wizard.CHOOSEDB.keepdata.Value
                engine.use_local = wizard.CHOOSEDB.uselocal.Value
                engine.RAW_DATA_LOCATION = wizard.CHOOSEDB.raw_data_dir.Value
                opts = dict()
                for key in options.keys():
                    opts[key] = options[key].GetValue()
                engine.opts = opts
                
                # Connect
                try:
                    engine.get_cursor()
                except Exception as e:
                    wx.MessageBox("There was an error with your database" 
                                  + " connection. \n\n" +
                                  e.__str__())
                    app.Exit()
                    return
                
                oldstdout = sys.stdout
                sys.stdout = update_dialog(self)
                
                # Download scripts
                errors = []
                for script in scripts:
                    scriptnum += 1
                    msg = "Downloading " + script.name
                    if len(scripts) > 0:
                        msg += " (" + str(scriptnum) + " of " + str(len(scripts)) + ")"
                    msg += " . . ."                               
                    try:
                        script.download(engine)
                    except UserSkipped:
                        errors.append("Skipped " + script.name + ".")
                    except UserAborted:
                        sys.stdout = oldstdout
                        self.dialog.Destroy()                
                        wx.MessageBox("Cancelled.")
                        final_cleanup(engine)
                        sys.exit()
                    except Exception as e:
                        errors.append("There was an error downloading " + 
                                      script.name + ".")
                        wx.MessageBox(e.__str__(), "Error")
                        raise
                        
                print "Finishing . . ."
                final_cleanup(engine)
                self.dialog.Update(len(scripts) + 1, "Finished!")
                if errors:
                    wx.MessageBox("The following errors occurred: \n" + 
                                  '\n'.join(errors))
                else:
                    wx.MessageBox("Your downloads were completed successfully.")
                    
                                    
                app.Exit()
    else:
        return
        
    frame = Frame()
    frame.Show(False)
    app.MainLoop()
